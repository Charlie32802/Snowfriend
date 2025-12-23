#!/usr/bin/env python3
"""
Django Project Structure Visualizer
Shows only important files and directories, excluding common development artifacts
"""

import os
import sys
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

    def is_important(self, name, is_dir=False):
        """Check if a file/directory is important to show"""
        if is_dir:
            # Show Django-specific directories
            if name in self.django_specific_dirs:
                return True
            # Show app directories (typically have models.py, views.py, etc.)
            if Path(name).joinpath('models.py').exists() or \
               Path(name).joinpath('views.py').exists() or \
               Path(name).joinpath('urls.py').exists():
                return True
            return False
        
        # Important files
        if name in self.important_dirs:
            return True
        
        # Django and Python project files
        important_extensions = {'.py', '.html', '.css', '.js', '.json', '.yml', '.yaml', 
                               '.md', '.txt', '.toml', '.ini', '.cfg', '.sh', '.sql'}
        return any(name.endswith(ext) for ext in important_extensions)

    def print_tree(self, directory=None, prefix="", is_last=True, depth=0, max_depth=3):
        """Print the directory tree structure"""
        if depth > max_depth:
            return
            
        if directory is None:
            directory = self.root_dir
        
        # Get all items, sorted and filtered
        items = []
        try:
            for item in sorted(directory.iterdir()):
                if not self.should_exclude(item, item.name):
                    # Only show important items at deeper levels
                    if depth > 0 and not self.is_important(item.name, item.is_dir()):
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
                self.print_tree(item, child_prefix, is_last_item, depth + 1, max_depth)
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
            '.js': '📜',
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
            'requirements.txt': '📦'
        }
        
        for ext, icon in icons.items():
            if filename.endswith(ext) or filename.lower() == ext:
                return icon
        
        return '📄'

    def print_summary(self):
        """Print a summary of important Django files"""
        print("\n" + "="*60)
        print("📊 DJANGO PROJECT STRUCTURE SUMMARY")
        print("="*60)
        
        important_files = {
            'Project Configuration': ['manage.py', 'requirements.txt', 'pyproject.toml'],
            'Django Settings': ['settings.py', 'urls.py', 'wsgi.py', 'asgi.py'],
            'Application Files': ['models.py', 'views.py', 'admin.py', 'apps.py', 'tests.py'],
            'Templates & Static': ['templates/', 'static/', 'media/'],
            'Configuration': ['.env.example', '.gitignore', 'docker-compose.yml']
        }
        
        for category, files in important_files.items():
            print(f"\n{category}:")
            for file in files:
                path = self.root_dir / file
                if path.exists():
                    print(f"  ✓ {file}")
                else:
                    # Check in subdirectories for some files
                    if file.endswith('.py'):
                        found = False
                        for py_file in self.root_dir.rglob(file):
                            if py_file.is_file():
                                print(f"  ✓ {py_file.relative_to(self.root_dir)}")
                                found = True
                                break
                        if not found:
                            print(f"  ✗ {file} (not found)")
                    else:
                        print(f"  ✗ {file} (not found)")

    def visualize(self, show_summary=True):
        """Main visualization method"""
        print(f"\n📂 Project Root: {self.root_dir}")
        print("="*60)
        print("🌳 Clean Django Project Structure (excluding development artifacts)")
        print("="*60)
        
        self.print_tree()
        
        if show_summary:
            self.print_summary()

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
        default=3,
        help='Maximum depth to display (default: 3)'
    )
    parser.add_argument(
        '--no-summary',
        action='store_true',
        help='Do not show the summary section'
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
    
    # Override max_depth if specified
    visualizer.print_tree = lambda d=None, p="", il=True, de=0, md=args.depth: \
        DjangoProjectVisualizer.print_tree(visualizer, d, p, il, de, md)
    
    visualizer.visualize(show_summary=not args.no_summary)

if __name__ == "__main__":
    main()