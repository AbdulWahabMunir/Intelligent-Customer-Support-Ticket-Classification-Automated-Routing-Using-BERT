"""Build the comparison notebook and execute both report notebooks."""
import os
from pathlib import Path
import subprocess
import sys

import nbformat
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


def main():
    notebook = nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_markdown_cell('# Model comparison and engineering trade-offs\n\nRecorded results from completed experiments. This notebook reads saved reports and does not tune on test data or train at deployment.'),
        nbformat.v4.new_code_cell("from pathlib import Path\nimport json\nimport pandas as pd\nROOT = Path.cwd()\nif not (ROOT / 'reports').exists():\n    ROOT = ROOT.parent\nbaselines = json.loads((ROOT / 'reports/baselines/metrics.json').read_text())\ntransformer = json.loads((ROOT / 'reports/distilbert/test_metrics.json').read_text())\nprint('Baseline selection:', baselines['selected_model'])\nprint('DistilBERT report sections:', list(transformer))\ndisplay(pd.DataFrame([{**{'model':name}, **{key:row['test'][key] for key in ['accuracy','macro_f1','weighted_f1']}} for name,row in baselines['models'].items()]))"),
        nbformat.v4.new_code_cell("from IPython.display import Markdown, display\ndisplay(Markdown((ROOT / 'reports/distilbert/comparison.md').read_text()))\ndisplay(Markdown((ROOT / 'reports/confidence/report.md').read_text()))"),
        nbformat.v4.new_code_cell("similarity = json.loads((ROOT / 'reports/similarity_audit.json').read_text())\ndisplay(pd.DataFrame([similarity]))\ndisplay(Markdown((ROOT / 'reports/robustness-pilot/report.md').read_text()))"),
        nbformat.v4.new_code_cell("display(Markdown((ROOT / 'reports/banking77/report.md').read_text()))"),
        nbformat.v4.new_markdown_cell('## Interpretation\n\nBitext has synthetic linguistic variants: exact deduplication does not remove shared templates. The draft robustness set is a diagnostic, not independently human-reviewed ground truth. BANKING77 is a separate domain/taxonomy baseline experiment, not a cross-domain score for the deployed model. The latency comparison was measured on the same local CPU; cloud cold starts and free-tier throttling differ. Priority labels come from business rules, and raw model scores remain uncalibrated.'),
    ])
    notebook.metadata.kernelspec = {'display_name': 'Support Project', 'language': 'python', 'name': 'support-project'}
    nbformat.write(notebook, ROOT / 'notebooks/03_model_comparison.ipynb')
    prefix = ROOT / 'artifacts/jupyter'
    subprocess.run([sys.executable, '-m', 'ipykernel', 'install', '--prefix', str(prefix), '--name', 'support-project', '--display-name', 'Support Project'], check=True)
    os.environ['JUPYTER_PATH'] = str(prefix / 'share/jupyter')
    for name in ['01_data_exploration.ipynb', '03_model_comparison.ipynb']:
        path = ROOT / 'notebooks' / name
        notebook = nbformat.read(path, as_version=4)
        NotebookClient(notebook, timeout=180, kernel_name='support-project', resources={'metadata': {'path': str(ROOT)}}).execute()
        nbformat.write(notebook, path)
        print('Executed ' + name, flush=True)


if __name__ == '__main__':
    main()
