"""
Setup script for IR Search Engine.
Run this after cloning the repository to set up the development environment.
"""
import os
import sys
import subprocess
import secrets


def print_step(step_num, message):
    """Print a formatted step message."""
    print(f"\n{'='*60}")
    print(f"Step {step_num}: {message}")
    print('='*60)


def run_command(command, description):
    """Run a shell command and handle errors."""
    print(f"\n→ {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Error: {e}")
        if e.stderr:
            print(e.stderr)
        return False


def create_env_file():
    """Create .env file from template."""
    if os.path.exists('.env'):
        response = input("\n.env file already exists. Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("Skipping .env creation.")
            return
    
    # Generate a secure secret key
    secret_key = secrets.token_urlsafe(50)
    
    with open('.env.example', 'r') as f:
        content = f.read()
    
    # Replace placeholder with actual secret key
    content = content.replace('your-secret-key-here-change-in-production', secret_key)
    
    with open('.env', 'w') as f:
        f.write(content)
    
    print("✓ Created .env file with secure SECRET_KEY")


def main():
    """Main setup function."""
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║         IR Search Engine - Setup Script                  ║
    ║         Version 2.0.0                                     ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Error: Python 3.8 or higher is required.")
        sys.exit(1)
    
    print(f"✓ Python version: {sys.version.split()[0]}")
    
    # Step 1: Create virtual environment
    print_step(1, "Creating Virtual Environment")
    if not os.path.exists('venv'):
        if run_command(f'{sys.executable} -m venv venv', 'Creating virtual environment'):
            print("✓ Virtual environment created")
        else:
            print("✗ Failed to create virtual environment")
            sys.exit(1)
    else:
        print("✓ Virtual environment already exists")
    
    # Determine activation command
    if sys.platform == 'win32':
        activate_cmd = 'venv\\Scripts\\activate'
        pip_cmd = 'venv\\Scripts\\pip'
        python_cmd = 'venv\\Scripts\\python'
    else:
        activate_cmd = 'source venv/bin/activate'
        pip_cmd = 'venv/bin/pip'
        python_cmd = 'venv/bin/python'
    
    # Step 2: Install dependencies
    print_step(2, "Installing Dependencies")
    if run_command(f'{pip_cmd} install --upgrade pip', 'Upgrading pip'):
        print("✓ Pip upgraded")
    
    if run_command(f'{pip_cmd} install -r requirements.txt', 'Installing requirements'):
        print("✓ Dependencies installed")
    else:
        print("✗ Failed to install dependencies")
        sys.exit(1)
    
    # Step 3: Create .env file
    print_step(3, "Creating Environment Configuration")
    create_env_file()
    
    # Step 4: Create logs directory
    print_step(4, "Creating Directories")
    os.makedirs('logs', exist_ok=True)
    os.makedirs('media/documents', exist_ok=True)
    print("✓ Created logs and media directories")
    
    # Step 5: Download NLTK data
    print_step(5, "Downloading NLTK Data")
    nltk_script = """
import nltk
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
print('✓ NLTK data downloaded')
"""
    with open('_temp_nltk.py', 'w') as f:
        f.write(nltk_script)
    
    run_command(f'{python_cmd} _temp_nltk.py', 'Downloading NLTK data')
    os.remove('_temp_nltk.py')
    
    # Step 6: Run migrations
    print_step(6, "Setting Up Database")
    if run_command(f'{python_cmd} manage.py migrate', 'Running migrations'):
        print("✓ Database migrations completed")
    else:
        print("✗ Failed to run migrations")
        sys.exit(1)
    
    # Step 7: Create superuser prompt
    print_step(7, "Create Superuser")
    response = input("\nWould you like to create a superuser now? (Y/n): ")
    if response.lower() != 'n':
        subprocess.run(f'{python_cmd} manage.py createsuperuser', shell=True)
    
    # Step 8: Load sample data
    print_step(8, "Load Sample Data")
    response = input("\nWould you like to load sample documents? (Y/n): ")
    if response.lower() != 'n':
        if run_command(f'{python_cmd} manage.py load_samples', 'Loading sample documents'):
            print("✓ Sample documents loaded")
            if run_command(f'{python_cmd} manage.py index_docs', 'Building search index'):
                print("✓ Search index built")
    
    # Final instructions
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║                 Setup Complete! 🎉                        ║
    ╚═══════════════════════════════════════════════════════════╝
    
    Next steps:
    
    1. Activate the virtual environment:
       Windows: {activate_win}
       Linux/Mac: {activate_unix}
    
    2. Review and update .env file if needed:
       - Set DEBUG=True for development
       - Configure database settings
       - Set up Redis if available
    
    3. Start the development server:
       python manage.py runserver
    
    4. Access the application:
       http://localhost:8000
    
    5. Access the admin panel:
       http://localhost:8000/admin
    
    For production deployment, see DEPLOYMENT.md
    For API usage, see API_DOCUMENTATION.md
    
    Happy searching! 🔍
    """.format(
        activate_win='venv\\Scripts\\activate',
        activate_unix='source venv/bin/activate'
    ))


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n✗ Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n✗ Setup failed with error: {e}")
        sys.exit(1)
