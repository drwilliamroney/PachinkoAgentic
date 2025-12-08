del /q dist\*
python -m build
echo to upload: python -m twine upload --verbose dist/*

