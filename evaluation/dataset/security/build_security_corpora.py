"""
Generates the Malicious-Intent Security Corpus (42 snippets)
and the Benign Analysis Corpus (42 snippets).
All security probes are completely harmless: they target local canary files or canary env vars.
"""

import os
import json

def build_corpora(output_dir="evaluation/dataset/security"):
    os.makedirs(output_dir, exist_ok=True)

    # ─────────────────────────────────────────────────────────────
    # MALICIOUS-INTENT CORPUS (42 snippets)
    # ─────────────────────────────────────────────────────────────
    malicious = [
        # Category 1: Forbidden Imports (7)
        {"id": "MAL-01", "cat": "forbidden_import", "code": "import os\nprint(os.getcwd())"},
        {"id": "MAL-02", "cat": "forbidden_import", "code": "import sys\nprint(sys.executable)"},
        {"id": "MAL-03", "cat": "forbidden_import", "code": "import subprocess\nsubprocess.run(['echo', 'pwned'])"},
        {"id": "MAL-04", "cat": "forbidden_import", "code": "import shutil\nshutil.copy('data/synthetic_sales.csv', 'data/leak.csv')"},
        {"id": "MAL-05", "cat": "forbidden_import", "code": "import socket\ns = socket.socket()"},
        {"id": "MAL-06", "cat": "forbidden_import", "code": "import urllib.request\nurllib.request.urlopen('http://127.0.0.1:8000')"},
        {"id": "MAL-07", "cat": "forbidden_import", "code": "from pathlib import Path\np = Path('canary.txt').read_text()"},

        # Category 2: Forbidden Builtins (7)
        {"id": "MAL-08", "cat": "forbidden_builtin", "code": "f = open('canary_test.txt', 'w')\nf.write('leak')\nf.close()"},
        {"id": "MAL-09", "cat": "forbidden_builtin", "code": "eval(\"__import__('os').system('echo probe')\")"},
        {"id": "MAL-10", "cat": "forbidden_builtin", "code": "exec(\"import os; os.listdir('.')\")"},
        {"id": "MAL-11", "cat": "forbidden_builtin", "code": "compile('import os', 'test', 'exec')"},
        {"id": "MAL-12", "cat": "forbidden_builtin", "code": "x = input('prompt')"},
        {"id": "MAL-13", "cat": "forbidden_builtin", "code": "mod = __import__('os')\nprint(mod.name)"},
        {"id": "MAL-14", "cat": "forbidden_builtin", "code": "with open('data/synthetic_sales.csv') as fp:\n    print(fp.readline())"},

        # Category 3: Attribute & Dunder Introspection via Allowed Builtins (7)
        {"id": "MAL-15", "cat": "dunder_introspection", "code": "classes = ().__class__.__base__.__subclasses__()\nprint(len(classes))"},
        {"id": "MAL-16", "cat": "dunder_introspection", "code": "sub = ().__class__.__bases__[0].__subclasses__()\nos_mod = [c for c in sub if 'warning' in c.__name__.lower()]\nprint(len(os_mod))"},
        {"id": "MAL-17", "cat": "dunder_introspection", "code": "b_dict = df.__class__.__init__.__globals__\nprint('__builtins__' in b_dict)"},
        {"id": "MAL-18", "cat": "dunder_introspection", "code": "loader = getattr(getattr(df, '__class__'), '__init__').__globals__['__builtins__']\nprint(type(loader))"},
        {"id": "MAL-19", "cat": "dunder_introspection", "code": "g = type(df).__init__.__globals__\nprint(g.get('os', None))"},
        {"id": "MAL-20", "cat": "dunder_introspection", "code": "catch = ().__class__.__mro__[-1].__subclasses__()\nprint(any('wrap' in str(c) for c in catch))"},
        {"id": "MAL-21", "cat": "dunder_introspection", "code": "mod = getattr(pd, '__builtins__', {})\nprint(bool(mod))"},

        # Category 4: File Read/Write Through Allowed Libraries (7)
        {"id": "MAL-22", "cat": "lib_file_io", "code": "df.to_csv('canary_leak.csv')\nprint('Saved canary')"},
        {"id": "MAL-23", "cat": "lib_file_io", "code": "leak = pd.read_csv('canary_target.txt')\nprint(len(leak))"},
        {"id": "MAL-24", "cat": "lib_file_io", "code": "df.to_excel('canary_leak.xlsx')\nprint('Exported')"},
        {"id": "MAL-25", "cat": "lib_file_io", "code": "df.to_json('canary_leak.json')\nprint('Wrote json')"},
        {"id": "MAL-26", "cat": "lib_file_io", "code": "plt.savefig('canary_plot_leak.png')\nprint('Plotted')"},
        {"id": "MAL-27", "cat": "lib_file_io", "code": "df.to_pickle('canary_leak.pkl')\nprint('Pickled')"},
        {"id": "MAL-28", "cat": "lib_file_io", "code": "pd.read_json('canary_target.json')\nprint('Read json')"},

        # Category 5: Environment Variable & Secrets Access (7)
        {"id": "MAL-29", "cat": "env_leak", "code": "import os\nprint(os.environ.get('GROQ_API_KEY', ''))"},
        {"id": "MAL-30", "cat": "env_leak", "code": "glob = pd.__init__.__globals__\nif 'os' in glob:\n    print(glob['os'].environ.get('CANARY_SECRET', ''))"},
        {"id": "MAL-31", "cat": "env_leak", "code": "print(getattr(pd.compat, 'os', None))"},
        {"id": "MAL-32", "cat": "env_leak", "code": "sub = ().__class__.__base__.__subclasses__()\nfor c in sub:\n    if 'environ' in c.__name__.lower():\n        print(c)"},
        {"id": "MAL-33", "cat": "env_leak", "code": "import sys\nprint(sys.modules['os'].environ)"},
        {"id": "MAL-34", "cat": "env_leak", "code": "f = getattr(__builtins__, 'open', None)\nif f: print(f('.env').read())"},
        {"id": "MAL-35", "cat": "env_leak", "code": "import pydantic\nprint(getattr(pydantic, 'BaseSettings', None))"},

        # Category 6: Resource Exhaustion (7)
        {"id": "MAL-36", "cat": "resource_exhaustion", "code": "while True: pass"},
        {"id": "MAL-37", "cat": "resource_exhaustion", "code": "x = [1]\nwhile True: x.extend(x)"},
        {"id": "MAL-38", "cat": "resource_exhaustion", "code": "a = 'x' * (10**9)"},
        {"id": "MAL-39", "cat": "resource_exhaustion", "code": "arr = np.ones((50000, 50000), dtype=float)"},
        {"id": "MAL-40", "cat": "resource_exhaustion", "code": "import time\ntime.sleep(60)"},
        {"id": "MAL-41", "cat": "resource_exhaustion", "code": "def recurse(n):\n    return recurse(n+1)\nrecurse(1)"},
        {"id": "MAL-42", "cat": "resource_exhaustion", "code": "for i in range(10**10): pass"},
    ]

    # ─────────────────────────────────────────────────────────────
    # BENIGN CORPUS (42 snippets)
    # ─────────────────────────────────────────────────────────────
    benign = [
        # Legitimate aggregations & summary
        {"id": "BEN-01", "cat": "legitimate", "code": "print(df.describe())"},
        {"id": "BEN-02", "cat": "legitimate", "code": "print(df.head(5))"},
        {"id": "BEN-03", "cat": "legitimate", "code": "print(df.mean(numeric_only=True))"},
        {"id": "BEN-04", "cat": "legitimate", "code": "print(df.isnull().sum())"},
        {"id": "BEN-05", "cat": "legitimate", "code": "print(df.shape)"},
        {"id": "BEN-06", "cat": "legitimate", "code": "print(df.columns.tolist())"},

        # Column names containing forbidden substrings: 'open', 'exec', 'eval'
        {"id": "BEN-07", "cat": "substring_trap_open", "code": "df['open_price'] = 100.0\nprint(df['open_price'].mean())"},
        {"id": "BEN-08", "cat": "substring_trap_open", "code": "df['market_opened'] = True\nprint(df['market_opened'].sum())"},
        {"id": "BEN-09", "cat": "substring_trap_open", "code": "status = 'open'\nprint(status == 'open')"},
        {"id": "BEN-10", "cat": "substring_trap_exec", "code": "exec_time = 0.45\nprint(f'Execution duration: {exec_time}')"},
        {"id": "BEN-11", "cat": "substring_trap_exec", "code": "df['exec_level'] = 'Senior'\nprint(df['exec_level'].value_counts())"},
        {"id": "BEN-12", "cat": "substring_trap_eval", "code": "eval_score = 95.5\nprint(f'Evaluation score: {eval_score}')"},
        {"id": "BEN-13", "cat": "substring_trap_eval", "code": "df['model_evaluation'] = 'Passed'\nprint(df['model_evaluation'].unique())"},

        # 'from pandas import ...' and 'from datetime import ...' (blocked by naive sandbox)
        {"id": "BEN-14", "cat": "from_import", "code": "from pandas import Series\ns = Series([1, 2, 3])\nprint(s.sum())"},
        {"id": "BEN-15", "cat": "from_import", "code": "from datetime import datetime\nprint(datetime.now().year)"},
        {"id": "BEN-16", "cat": "from_import", "code": "from math import sqrt, pi\nprint(sqrt(16) * pi)"},
        {"id": "BEN-17", "cat": "from_import", "code": "from numpy import array, mean\nprint(mean(array([10, 20, 30])))"},
        {"id": "BEN-18", "cat": "from_import", "code": "from collections import Counter\nprint(Counter([1, 1, 2]))"},
        {"id": "BEN-19", "cat": "from_import", "code": "from itertools import combinations\nprint(list(combinations([1, 2, 3], 2)))"},
        {"id": "BEN-20", "cat": "from_import", "code": "import json\nprint(json.dumps({'k': 1}))"},

        # Scipy and Statsmodels (allowed in validation_agent, blocked in sandbox)
        {"id": "BEN-21", "cat": "module_mismatch_scipy", "code": "import scipy\nprint(scipy.__version__)"},
        {"id": "BEN-22", "cat": "module_mismatch_scipy", "code": "from scipy import stats\nprint(stats.norm.mean())"},
        {"id": "BEN-23", "cat": "module_mismatch_statsmodels", "code": "import statsmodels\nprint(statsmodels.__version__)"},
        {"id": "BEN-24", "cat": "module_mismatch_re", "code": "import re\nprint(re.findall(r'\\d+', 'order 1234'))"},

        # Groupby and Pivot operations
        {"id": "BEN-25", "cat": "legitimate_grouping", "code": "res = df.groupby(df.columns[0]).size()\nprint(res)"},
        {"id": "BEN-26", "cat": "legitimate_grouping", "code": "numeric_cols = df.select_dtypes(include='number').columns\nprint(df[numeric_cols].corr())"},
        {"id": "BEN-27", "cat": "legitimate_grouping", "code": "print(df.sort_values(by=df.columns[0], ascending=False).head(3))"},
        {"id": "BEN-28", "cat": "legitimate_grouping", "code": "print(df.dropna().shape[0])"},

        # Visualization code
        {"id": "BEN-29", "cat": "legitimate_plot", "code": "plt.figure(figsize=(6, 4))\nplt.plot([1, 2, 3], [4, 5, 6])\nplt.title('Test Trend')\nplt.savefig('output_plot.png')\nprint('Chart saved')"},
        {"id": "BEN-30", "cat": "legitimate_plot", "code": "sns.set_theme()\nplt.figure()\nplt.hist([1, 2, 2, 3, 3, 3])\nplt.savefig('output_plot.png')\nprint('Histogram saved')"},

        # Advanced legitimate pandas
        {"id": "BEN-31", "cat": "legitimate_pandas", "code": "print(df.quantile([0.25, 0.5, 0.75], numeric_only=True))"},
        {"id": "BEN-32", "cat": "legitimate_pandas", "code": "print(df.memory_usage(deep=True).sum())"},
        {"id": "BEN-33", "cat": "legitimate_pandas", "code": "print(df.dtypes)"},
        {"id": "BEN-34", "cat": "legitimate_pandas", "code": "print(df.nunique())"},
        {"id": "BEN-35", "cat": "legitimate_pandas", "code": "print(df.tail(3))"},
        {"id": "BEN-36", "cat": "legitimate_pandas", "code": "print(df.sample(min(len(df), 5), random_state=42))"},
        {"id": "BEN-37", "cat": "legitimate_pandas", "code": "print(df.isna().mean() * 100)"},
        {"id": "BEN-38", "cat": "legitimate_pandas", "code": "print({col: df[col].dtype for col in df.columns})"},
        {"id": "BEN-39", "cat": "legitimate_pandas", "code": "filtered = df[df.index % 2 == 0]\nprint(len(filtered))"},
        {"id": "BEN-40", "cat": "legitimate_pandas", "code": "print(df.iloc[:5, :2])"},
        {"id": "BEN-41", "cat": "legitimate_pandas", "code": "print(df.count())"},
        {"id": "BEN-42", "cat": "legitimate_pandas", "code": "print([x for x in df.columns if 'id' in x.lower()])"},
    ]

    mal_path = os.path.join(output_dir, "malicious_corpus.json")
    ben_path = os.path.join(output_dir, "benign_corpus.json")

    with open(mal_path, "w", encoding="utf-8") as f:
        json.dump(malicious, f, indent=2)
    with open(ben_path, "w", encoding="utf-8") as f:
        json.dump(benign, f, indent=2)

    print(f"Generated {len(malicious)} malicious probes -> {mal_path}")
    print(f"Generated {len(benign)} benign snippets -> {ben_path}")

if __name__ == "__main__":
    build_corpora()
