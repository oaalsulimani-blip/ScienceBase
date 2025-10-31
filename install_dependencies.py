import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error in {description}:")
        print(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error in {description}: {str(e)}")
        return False

def check_python_version():
    print("🐍 Checking Python version...")
    if sys.version_info < (3, 7):
        print(f"❌ Python 3.7 or higher is required. Current version: {sys.version}")
        return False
    print(f"✅ Python version {sys.version} is compatible")
    return True

def upgrade_pip():
    return run_command(
        f'"{sys.executable}" -m pip install --upgrade pip',
        "Upgrading pip"
    )

def install_requirements():
    if not Path("requirements.txt").exists():
        print("❌ requirements.txt not found. Creating default one...")
        create_default_requirements()
    
    return run_command(
        f'"{sys.executable}" -m pip install -r requirements.txt',
        "Installing packages from requirements.txt"
    )

def create_default_requirements():
    requirements_content = """pandas>=1.5.0
numpy>=1.21.0
streamlit>=1.28.0
plotly>=5.15.0
requests>=2.28.0
beautifulsoup4>=4.11.0
schedule>=1.2.0
sqlalchemy>=2.0.0
python-dotenv>=1.0.0
openpyxl>=3.1.0
scholarly>=1.7.0
lxml>=4.9.0
fake-useragent>=1.1.0
"""
    with open("requirements.txt", "w") as f:
        f.write(requirements_content)
    print("✅ Created default requirements.txt")

def verify_installation():
    print("\n🔍 Verifying package installation...")
    
    packages_to_check = [
        "pandas", "numpy", "streamlit", "plotly", "requests",
        "beautifulsoup4", "schedule", "sqlalchemy", "python_dotenv", 
        "openpyxl", "scholarly", "lxml", "fake_useragent"
    ]
    
    all_installed = True
    for package in packages_to_check:
        try:
            if package == "python_dotenv":
                __import__("dotenv")
            else:
                __import__(package)
            print(f"✅ {package} is installed")
        except ImportError as e:
            print(f"❌ {package} is NOT installed: {e}")
            all_installed = False
    
    return all_installed

def main():
    print("=" * 60)
    print("📦 Scholarly Metrics Dashboard - Dependency Installer")
    print("=" * 60)
    
    if not check_python_version():
        sys.exit(1)
    
    if not upgrade_pip():
        print("⚠️  Pip upgrade failed, but continuing...")
    
    if not install_requirements():
        print("❌ Failed to install some packages")
        sys.exit(1)
    
    if not verify_installation():
        print("❌ Some packages failed to install properly")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 All dependencies installed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Add your ORCID data to data_ORCIDs.xlsx")
    print("2. Run: python scripts_data_pipeline.py (for initial setup)")
    print("3. Run: python run_dashboard.py (to start the dashboard)")
    print("4. Run: python run_scheduler.py (for automatic updates)")

if __name__ == "__main__":
    main()