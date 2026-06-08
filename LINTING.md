# Linting & Code Cleaning Guide

This project uses **Ruff** for Python files and **djLint** for HTML templates. Both tools check for syntax issues, format style errors, and security slips.

---

## 🐍 Python (Backend)

Run these commands in your terminal to check or clean your Python files:

### 1. Scan for errors (Check)
See what is broken or out of line without modifying your code:
```bash
ruff check .
```

### 2. Auto-fix errors

Let the tool automatically fix safe errors (like unused imports or minor formatting slips) for you:

```bash
ruff check . --fix
```

### 3. Reformat code layout

Instantly clean up your indentations, line lengths, and spacing rules across the whole project:

```bash
ruff format .
```

---

## 🎨 HTML / Jinja (Templates)

Run these commands to check or format files inside your web layout directories:

### 1. Scan for template errors

Check your HTML formatting, unclosed tags, or messy template variables:

```bash
djlint templates/ --check
```

### 2. Auto-format all templates

Instantly correct nested indentations and clean up quote layouts in your templates folder:

```bash
djlint templates/ --reformat
```
