import os
import shutil
import datetime

def perform_backup(target_root: str = r"D:\projects\Ai-Job-Search_backups") -> str:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target_dir = os.path.join(target_root, timestamp)
    os.makedirs(target_dir, exist_ok=True)

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(base_dir, "sql_app.db")
    uploads_path = os.path.join(base_dir, "uploads")

    if os.path.exists(db_path):
        dest_db = os.path.join(target_dir, "sql_app.db")
        shutil.copy2(db_path, dest_db)
        print(f"Backed up database ({os.path.getsize(db_path)} bytes) to {dest_db}")
    else:
        print(f"Database not found at {db_path}")

    if os.path.exists(uploads_path):
        dest_uploads = os.path.join(target_dir, "uploads")
        shutil.copytree(uploads_path, dest_uploads, dirs_exist_ok=True)
        print(f"Backed up uploads folder to {dest_uploads}")
    else:
        print(f"Uploads directory not found at {uploads_path}")

    print(f"Backup successfully completed at: {target_dir}")
    return target_dir

if __name__ == "__main__":
    perform_backup()
