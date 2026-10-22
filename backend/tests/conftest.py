import os
from pathlib import Path
DB=Path(__file__).parent/'test.db'
if DB.exists(): DB.unlink()
os.environ['DATABASE_URL']=f'sqlite:///{DB}'
os.environ['TOKEN_SECRET']='test-secret-123456'
os.environ['ALLOW_TEST_ENDPOINTS']='true'
