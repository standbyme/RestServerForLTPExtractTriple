FROM python:2.7.14
COPY requirement.txt /requirement.txt
RUN pip install -r requirement.txt
COPY relation_triple_extraction_RULE.py /relation_triple_extraction_RULE.py
EXPOSE 1234
CMD ["python","/index.py"]