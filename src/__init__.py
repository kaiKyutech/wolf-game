"""プロジェクト共通の初期化処理。"""
from src.config.env import load_project_dotenv

# NotebookやCLIからインポートされたタイミングで.envを読み込む
load_project_dotenv()
