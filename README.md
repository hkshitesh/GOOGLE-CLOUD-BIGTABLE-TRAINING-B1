## Link for VM and Google Cloud Sheet

https://docs.google.com/spreadsheets/d/1TurJ-L1zUo1e_9SdDc2N-lH0o_JSU_TZu5KdbaLiCqs/edit?usp=sharing

## IMPORTANT COMMANDS
  
  python3 -m venv venv
  
  source venv/bin/activate
  
  pip install google-cloud-bigtable


## Command

gcloud projects remove-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT" \
    --role="roles/editor"


gcloud projects get-iam-policy $PROJECT_ID \
    --flatten="bindings[].members" \
    --filter="bindings.members:user:hitesh@datacouch.io" \
    --format="table(bindings.role,bindings.members)"

## FINAL FEEDBACK

https://forms.gle/4J63AA4XzQPMixwg9

