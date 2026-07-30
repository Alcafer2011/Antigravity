import os
from huggingface_hub import snapshot_download
os.environ['HF_TOKEN'] = os.environ.get('HF_TOKEN','')
repo = 'test/modello'
pat = "*.gguf"
local = '/kaggle/working/models/' + repo.replace('/', '__') if os.path.exists('/kaggle') else ('./models/' + repo.replace('/', '__'))
os.makedirs(local, exist_ok=True)
snapshot_download(repo_id=repo, allow_patterns=pat, local_dir=local, token=os.environ['HF_TOKEN'])
print('SCARICATO IN:', local)
# --- SALVATAGGIO PERSISTENTE (Kaggle Dataset) ---
if os.path.exists('/kaggle'):
    ds = '/kaggle/working/' + repo.replace('/', '__') + '_dataset'
    os.makedirs(ds, exist_ok=True)
    os.system('cp -r ' + local + '/* ' + ds + '/')
    print('Ora crea il Dataset su Kaggle (una tantum):')
    print('  !kaggle datasets create -p ' + ds + ' -n modello-uncensored')
    print('Il modello resta sempre disponibile nel tuo Dataset, anche a notebook chiuso.')