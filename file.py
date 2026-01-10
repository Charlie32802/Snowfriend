#!/usr/bin/env python3
"""
Django Project Structure Visualizer
Shows only important files and directories, excluding common development artifacts
"""

from pathlib import Path

class DjangoProjectVisualizer:
    def __init__(self, root_dir="."):
        self.root_dir = Path(root_dir).resolve()
        self.exclude_dirs = {
            '__pycache__',
            '.git',
            '.idea',
            '.vscode',
            'venv',
            'env',
            'virtualenv',
            '.env',
            'node_modules',
            '.pytest_cache',
            '__pycache__',
            'migrations',
            '.mypy_cache',
            '.coverage',
            'htmlcov',
            'dist',
            'build',
            '*.egg-info',
            '.ipynb_checkpoints'
        }
        
        self.exclude_files = {
            '*.pyc',
            '*.pyo',
            '*.pyd',
            '.DS_Store',
            'db.sqlite3',
            '.coverage',
            'coverage.xml',
            '*.log',
            '*.pid',
            '*.pot',
            '*.mo',
            '.python-version',
            '.env',
            '.env.local',
            '.env.production',
            'requirements-dev.txt',
            'dev-requirements.txt'
        }
        
        self.important_dirs = {
            'manage.py',
            'requirements.txt',
            'pyproject.toml',
            'setup.py',
            'README.md',
            '.gitignore',
            'dockerfile',
            'docker-compose.yml',
            '.dockerignore'
        }
        
        self.django_specific_dirs = {
            'templates',
            'static',
            'media',
            'fixtures',
            'locale',
            'apps',
            'utils',
            'core'
        }
        
        # Default max depth - increased to show more levels
        self.max_depth = 5
        
        # Always show these directories completely
        self.always_show_dirs = {'static', 'templates', 'media'}
        
        # Also show subdirectories of these directories
        self.show_subdirs_of = {'css', 'js', 'images'}

    def should_exclude(self, path, name):
        """Check if a file/directory should be excluded"""
        # Check directories
        if path.is_dir():
            if name in self.exclude_dirs:
                return True
            if name.startswith('.') and name not in ['.gitignore']:
                return True
            return False
        
        # Check files
        if name in self.exclude_files:
            return True
        
        # Check patterns
        for pattern in self.exclude_files:
            if pattern.startswith('*') and name.endswith(pattern[1:]):
                return True
        
        # Exclude hidden files (except important ones)
        if name.startswith('.') and name not in self.important_dirs:
            return True
            
        return False

    def is_important(self, name, is_dir=False, path=None, parent_path=None):
        """Check if a file/directory is important to show"""
        # Always show Django-specific directories
        if is_dir and (name in self.always_show_dirs or (parent_path and parent_path.name in self.always_show_dirs)):
            return True
            
        # Show subdirectories of css, js, images
        if is_dir and parent_path and parent_path.name in self.show_subdirs_of:
            return True
            
        if is_dir:
            # Show Django-specific directories
            if name in self.django_specific_dirs:
                return True
            # Show app directories (typically have models.py, views.py, etc.)
            if path and path.is_dir():
                # Check for common Django app files
                app_files = ['models.py', 'views.py', 'apps.py', 'admin.py', 'urls.py']
                for app_file in app_files:
                    if (path / app_file).exists():
                        return True
            return False
        
        # Important files
        if name in self.important_dirs:
            return True
        
        # Django and Python project files including CSS/JS
        important_extensions = {'.py', '.html', '.css', '.js', '.scss', '.sass', '.ts', '.json', '.yml', '.yaml', 
                               '.md', '.txt', '.toml', '.ini', '.cfg', '.sh', '.sql', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg'}
        return any(name.endswith(ext) for ext in important_extensions)

    def print_tree(self, directory=None, prefix="", is_last=True, depth=0):
        """Print the directory tree structure"""
        if depth > self.max_depth:
            return
            
        if directory is None:
            directory = self.root_dir
        
        # Get all items, sorted and filtered
        items = []
        try:
            for item in sorted(directory.iterdir()):
                if not self.should_exclude(item, item.name):
                    # For static, templates, media directories and their subdirs - show all contents
                    if (directory.name in self.always_show_dirs or 
                        (directory.parent and directory.parent.name in self.always_show_dirs) or
                        directory.name in self.show_subdirs_of):
                        items.append(item)
                    else:
                        # Only show important items at deeper levels
                        if depth > 0 and not self.is_important(item.name, item.is_dir(), item, directory):
                            continue
                        items.append(item)
        except (PermissionError, OSError):
            return
        
        # Determine connector
        connector = "└── " if is_last else "├── "
        
        # Print current directory/item
        if directory == self.root_dir:
            print(f"📁 {directory.name}/")
        elif depth > 0:
            dir_name = directory.name + ("/" if directory.is_dir() else "")
            print(f"{prefix}{connector}{dir_name}")
        
        # Update prefix for children
        child_prefix = prefix + ("    " if is_last else "│   ")
        
        # Process children
        for i, item in enumerate(items):
            is_last_item = (i == len(items) - 1)
            
            if item.is_dir():
                # Directory
                print(f"{prefix}{'└── ' if is_last_item else '├── '}📁 {item.name}/")
                self.print_tree(item, child_prefix, is_last_item, depth + 1)
            else:
                # File
                # Get appropriate icon based on file type
                icon = self.get_file_icon(item.name)
                print(f"{prefix}{'└── ' if is_last_item else '├── '}{icon} {item.name}")

    def get_file_icon(self, filename):
        """Get icon for file based on extension"""
        icons = {
            '.py': '🐍',
            '.html': '🌐',
            '.css': '🎨',
            '.scss': '🎨',
            '.sass': '🎨',
            '.js': '📜',
            '.ts': '📜',
            '.json': '📋',
            '.md': '📖',
            '.txt': '📝',
            '.yml': '⚙️',
            '.yaml': '⚙️',
            '.toml': '⚙️',
            '.sql': '🗃️',
            '.sh': '💻',
            '.gitignore': '👁️',
            'dockerfile': '🐳',
            'requirements.txt': '📦',
            'manage.py': '⚙️',
            'settings.py': '⚙️',
            'urls.py': '🔗',
            'wsgi.py': '🌐',
            'asgi.py': '🌐',
            'models.py': '🗄️',
            'views.py': '👁️',
            'admin.py': '👨‍💼',
            'apps.py': '📱',
            'tests.py': '🧪',
            '.png': '🖼️',
            '.jpg': '🖼️',
            '.jpeg': '🖼️',
            '.gif': '🖼️',
            '.ico': '🖼️',
            '.svg': '🖼️'
        }
        
        # Try exact match first
        if filename.lower() in icons:
            return icons[filename.lower()]
        
        # Try file extension
        for ext, icon in icons.items():
            if filename.endswith(ext):
                return icon
        
        return '📄'

    def visualize(self, show_summary=False):
        """Main visualization method - now without summary by default"""
        print(f"\n📂 Project Root: {self.root_dir}")
        print("="*60)
        print("🌳 Clean Django Project Structure (excluding development artifacts)")
        print("="*60)
        
        self.print_tree()

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Visualize Django project structure, excluding development artifacts'
    )
    parser.add_argument(
        'path',
        nargs='?',
        default='.',
        help='Path to Django project root (default: current directory)'
    )
    parser.add_argument(
        '--depth',
        type=int,
        default=5,
        help='Maximum depth to display (default: 5)'
    )
    parser.add_argument(
        '--summary',
        action='store_true',
        help='Show the summary section (default: off)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Show all files (including normally excluded ones)'
    )
    
    args = parser.parse_args()
    
    visualizer = DjangoProjectVisualizer(args.path)
    
    if args.all:
        visualizer.exclude_dirs.clear()
        visualizer.exclude_files.clear()
    
    # Set max depth from command line argument
    visualizer.max_depth = args.depth
    
    # Show visualization with or without summary
    visualizer.visualize(show_summary=args.summary)

if __name__ == "__main__":
    main()