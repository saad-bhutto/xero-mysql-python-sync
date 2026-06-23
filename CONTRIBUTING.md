# Contributing to xero-mysql-python-sync

Thank you for your interest in contributing! This project welcomes bug reports, feature requests, and pull requests.

## Getting Started

1. **Fork** the repository on GitHub
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/xero-mysql-python-sync.git
   cd xero-mysql-python-sync
   ```
3. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

1. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy configuration files:
   ```bash
   cp .env.example .env
   cp local.settings.example.json local.settings.json
   ```
4. Fill in your Xero OAuth2 credentials and MySQL connection details.

5. Start a local MySQL instance using Docker:
   ```bash
   docker-compose up -d
   ```

6. Run the Azure Functions locally:
   ```bash
   func start
   ```

## Code Style

- Follow [PEP 8](https://pep8.org/) for Python code style.
- Use meaningful variable and function names.
- Add docstrings to all public functions and classes.
- Keep functions focused on a single responsibility.

## Submitting Changes

1. Ensure your changes work locally and do not break existing functionality.
2. Add or update tests if applicable.
3. Commit your changes with a clear, descriptive message:
   ```bash
   git commit -m "feat: add support for syncing Xero contacts to MySQL"
   ```
4. Push to your fork:
   ```bash
   git push origin feature/your-feature-name
   ```
5. Open a **Pull Request** against the `main` branch of this repository.

## Pull Request Guidelines

- Provide a clear description of what the PR does and why.
- Link to any relevant GitHub issues.
- Ensure the PR title is concise and descriptive.
- Make sure all credentials are replaced with placeholder values — never commit real secrets.
- Keep PRs focused: one feature or fix per PR makes review easier.

## Reporting Bugs

Please open a GitHub issue with:
- A clear description of the bug
- Steps to reproduce
- Expected vs actual behaviour
- Your Python version and OS

## Requesting Features

Open a GitHub issue describing:
- The feature you'd like to see
- Why it would be useful
- Any implementation ideas you have

## Security Issues

If you discover a security vulnerability, please **do not** open a public issue. Instead, email the maintainers directly. We will respond promptly.

## Code of Conduct

Be respectful and constructive. We welcome contributors of all experience levels.
