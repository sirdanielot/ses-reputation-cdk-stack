# How to create the Lambda Package

1. pip install --target ./lambda-package mysql-connector-python
2. (cd lambda-package && zip -r - .) > lambda-package.zip
3. zip -g lambda-package.zip lambda_function.py
4. rm -r lambda-package
