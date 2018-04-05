mkdir dist
pip install -r requirements.txt -t ./dist
cp runscope2slack.py dist/runscope2slack.py
cp handler.py dist/handler.py
cd dist
zip -r ../deploy.zip *
cd ..
