import json
import tempfile
import sys
from pathlib import Path
from io import BytesIO

# Add src to PYTHONPATH so redrob_ranker can be imported
sys.path.insert(0, str(Path(__file__).parent / "src"))

import streamlit as st
import pandas as pd

from redrob_ranker.pipeline import rank_candidates
from redrob_ranker.io import write_submission


st.set_page_config(page_title="Redrob Ranker Demo", layout="wide")

st.title("Redrob Candidate Discovery Ranker")
st.markdown("Upload a sample `candidates.jsonl` file to test the deterministic CPU-only ranking engine.")

uploaded_file = st.file_uploader("Upload candidates.jsonl", type=["jsonl"])

if uploaded_file is not None:
    if st.button("Run Ranker"):
        with st.spinner("Ranking candidates..."):
            # Streamlit uploads are stored in an in-memory buffer, we need to temporarily save it 
            # to disk so our file-based rank.py pipeline can process it natively
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jsonl") as tmp:
                tmp.write(uploaded_file.getvalue())
                tmp_path = Path(tmp.name)
            
            try:
                # Execute the deterministic ranking
                results = rank_candidates(tmp_path, limit=100)
                
                # Format to a readable dataframe table 
                display_data = []
                for rank, item in enumerate(results, start=1):
                    cand = item["candidate"]
                    prof = cand["profile"]
                    feats = item["features"]
                    
                    display_data.append({
                        "Rank": rank,
                        "Score": round(item["score"], 4),
                        "ID": cand["candidate_id"],
                        "Title": prof.get("current_title", ""),
                        "Tier": item["model_decision"].quality_tier,
                        "Title Fit": round(feats.title_fit, 2),
                        "JD Evidence": round(feats.jd_evidence, 2),
                        "Risk": round(max(feats.honeypot_risk, feats.trap_risk), 2),
                        "Reasoning": item["reasoning"]
                    })
                    
                df = pd.DataFrame(display_data)
                
                st.success(f"Ranked {len(results)} candidates successfully!")
                
                st.subheader("Ranked Results")
                st.dataframe(df, use_container_width=True)
                
                # Generate CSV buffer for the standard output download
                with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as out_csv:
                    out_csv_path = Path(out_csv.name)
                    write_submission(results, out_csv_path)
                    csv_bytes = out_csv_path.read_bytes()
                    
                st.download_button(
                    label="Download standard submission.csv",
                    data=csv_bytes,
                    file_name="submission.csv",
                    mime="text/csv"
                )
            finally:
                # Cleanup the ephemeral cache chunks
                if tmp_path.exists():
                    tmp_path.unlink()
                if 'out_csv_path' in locals() and out_csv_path.exists():
                    out_csv_path.unlink()
