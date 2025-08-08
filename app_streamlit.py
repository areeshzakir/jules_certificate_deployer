from pathlib import Path
import streamlit as st
import os, subprocess, uuid, shutil, zipfile, csv

"""
Streamlit one-page UI for certificate workflow.
- Upload CSV + Template PDF
- Validates CSV headers
- Runs ./certificate_workflow.sh <csv> <template> [output_dir]
- Shows logs and returns a ZIP of outputs
- Optional password via APP_PASS
"""

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "certificate_workflow.sh"
UPLOADS = ROOT / "uploads"
OUTPUTS = ROOT / "certificates"
TOKENS = ROOT / "tokens"
CREDENTIALS = ROOT / "credentials"
UPLOADS.mkdir(exist_ok=True)
OUTPUTS.mkdir(exist_ok=True)
TOKENS.mkdir(exist_ok=True)
CREDENTIALS.mkdir(exist_ok=True)

REQUIRED_COLS = [
    "name","email","certificate_id","course_type","completion_date",
    "college_name","mentor_name","mentor_signature","event_type"
]

st.set_page_config(page_title="Certificate Runner", layout="centered")
st.title("Certificate Runner (CSV → Certificates → Email)")

# Optional minimal password: set APP_PASS
app_pass = os.getenv("APP_PASS")
if app_pass:
    if "ok" not in st.session_state: st.session_state.ok = False
    if not st.session_state.ok:
        p = st.text_input("Enter password", type="password")
        if st.button("Login"): st.session_state.ok = (p == app_pass)
        if not st.session_state.ok: st.stop()

# Add some instructions
st.markdown("""
### Instructions:
1. Upload your CSV file with student data
2. Upload your certificate template PDF
3. Optionally specify an output folder name
4. Click 'Run workflow' to generate certificates and send emails

**Note:** The first run may take longer as dependencies are installed.
""")

csv_up = st.file_uploader("Upload CSV", type=["csv"])
pdf_up = st.file_uploader("Upload Certificate Template (PDF)", type=["pdf"])
outname = st.text_input("Output folder name (optional)", "")

# Add email sending toggle
send_emails = st.checkbox("Send emails after generating certificates", value=True)

run = st.button("Run workflow")
log_area = st.empty()
download_area = st.empty()

def _write(uploaded, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        f.write(uploaded.getbuffer())

def _zip_dir(src: Path, zip_path: Path):
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for p in src.rglob("*"):
            if p.is_file():
                zf.write(p, p.relative_to(src))
    return zip_path

def _validate_csv_headers(csv_path: Path):
    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        try:
            headers = next(reader)
        except StopIteration:
            return ["<empty csv>"], []
    norm = [h.strip().lower() for h in headers]
    missing = [c for c in REQUIRED_COLS if c not in norm]
    return missing, headers

if run:
    if not csv_up or not pdf_up:
        st.warning("Please upload both CSV and PDF.")
        st.stop()

    run_id = uuid.uuid4().hex[:8]
    run_dir = UPLOADS / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    csv_path = run_dir / "data.csv"; _write(csv_up, csv_path)
    tpl_path = run_dir / "template.pdf"; _write(pdf_up, tpl_path)

    # Validate headers
    missing, headers = _validate_csv_headers(csv_path)
    if missing:
        st.error(
            "CSV is missing required columns:\n- " +
            "\n- ".join(missing) +
            f"\n\nFound headers: {headers}"
        )
        st.stop()

    out_dir = OUTPUTS / (outname.strip() or f"run_{run_id}")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Pass RELATIVE paths (your bash uses $(pwd)/$CSV_FILE)
    csv_rel = os.path.relpath(csv_path, ROOT)
    tpl_rel = os.path.relpath(tpl_path, ROOT)
    out_rel = os.path.relpath(out_dir, ROOT)

    if not os.access(SCRIPT, os.X_OK):
        os.chmod(SCRIPT, 0o755)

    # Create .env file with email sending option
    env_path = ROOT / ".env"
    with open(env_path, "w") as f:
        f.write(f"""# Environment variables for Automated Student Email Workflow

# Using local CSV file
LOCAL_CSV_PATH={csv_path}

# Local certificates directory
CERTIFICATES_DIR={out_dir}

# Email settings
EMAIL_SUBJECT_TEMPLATE=Certificate of Participation
EMAIL_BODY_TEMPLATE=Dear {{name}},\n\nThank you for participating in our event. Please find attached your certificate of participation.\n\nBest regards,\nPlutus Education
""")

    # Modify command based on email sending preference
    cmd = [str(SCRIPT), csv_rel, tpl_rel, out_rel]
    
    env = os.environ.copy()
    cred = CREDENTIALS / "credentials.json"
    tok = TOKENS / "token.json"
    if cred.exists(): env["GOOGLE_APPLICATION_CREDENTIALS"] = str(cred)
    if tok.exists():  env["TOKEN_PATH"] = str(tok)

    # Add progress indicator
    with st.spinner("Running certificate workflow..."):
        try:
            # Run certificate generation
            proc = subprocess.run(
                cmd, cwd=str(ROOT), env=env, text=True,
                capture_output=True, check=False, timeout=3600
            )
            
            log_output = f">> Running:\n{' '.join(cmd)}\n\n" \
                       f">> STDOUT:\n{proc.stdout}\n\n" \
                       f">> STDERR:\n{proc.stderr}"
            
            log_area.code(log_output)

            # Create ZIP of certificates
            zip_path = run_dir / (out_dir.name + ".zip")
            _zip_dir(out_dir, zip_path)
            
            # Show download button
            with open(zip_path, "rb") as f:
                download_area.download_button(
                    "Download generated certificates (ZIP)",
                    f, file_name=zip_path.name
                )
                
            st.success(f"Done! Output: {out_dir}")
            
            # Show certificate preview if available
            certificate_files = list(out_dir.glob("*.pdf"))
            if certificate_files:
                st.subheader("Certificate Preview")
                with open(certificate_files[0], "rb") as f:
                    st.download_button(
                        "Download Sample Certificate",
                        f,
                        file_name=certificate_files[0].name,
                        mime="application/pdf"
                    )

        except subprocess.TimeoutExpired:
            st.error("Timed out. Try a smaller CSV.")
        except Exception as e:
            st.error(f"Error: {e}")