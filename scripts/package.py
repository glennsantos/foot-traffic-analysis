import fnmatch
import os
import time
import zipfile


EXCLUDES = [
    ".git*",
    "__pycache__",
    "*.pyc",
    "venv",
    ".venv",
    "cache",
    "analyses",
    "analyses_new",
    "reports",
    "dist",
    "app.log",
    ".idea",
    ".vscode",
    ".docker",
    "docker-compose.override.yml",
    ".DS_Store",
]


def is_excluded(path: str) -> bool:
    base = os.path.basename(path)
    for pattern in EXCLUDES:
        if fnmatch.fnmatch(base, pattern) or fnmatch.fnmatch(path, pattern):
            return True
    # Also exclude any path containing an excluded directory
    parts = path.split(os.sep)
    for part in parts:
        for pattern in EXCLUDES:
            if fnmatch.fnmatch(part, pattern):
                return True
    return False


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    dist_dir = os.path.join(root, "dist")
    os.makedirs(dist_dir, exist_ok=True)

    # Try to read version
    version = None
    version_file = os.path.join(root, "VERSION")
    if os.path.exists(version_file):
        with open(version_file, "r", encoding="utf-8") as vf:
            version = vf.read().strip()

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    if version:
        zip_name = f"foot-traffic-analysis_v{version}_{timestamp}.zip"
    else:
        zip_name = f"foot-traffic-analysis_{timestamp}.zip"
    zip_path = os.path.join(dist_dir, zip_name)

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for dirpath, dirnames, filenames in os.walk(root):
            # Compute relative path from root
            rel_dir = os.path.relpath(dirpath, root)
            if rel_dir == ".":
                rel_dir = ""

            # Filter directories in-place to prevent walking excluded dirs
            dirnames[:] = [d for d in dirnames if not is_excluded(os.path.join(rel_dir, d))]

            for filename in filenames:
                rel_file = os.path.join(rel_dir, filename) if rel_dir else filename
                if is_excluded(rel_file):
                    continue
                abs_file = os.path.join(dirpath, filename)
                zf.write(abs_file, arcname=rel_file)

    print(f"Created package: {zip_path}")


if __name__ == "__main__":
    main()
