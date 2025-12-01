 FROM python:3.13.9-slim-bookworm
 ENV PYTHONDONTWRITEBYTECODE=1
 ENV PYTHONUNBUFFERED=1
 RUN apt-get update
 RUN apt-get install -y libgl1
 RUN apt-get install -y libglib2.0-0
 RUN pip install Django
 RUN pip install easyocr
 RUN pip install python-docx
 RUN pip install crewai
 RUN pip install PyMuPDF
 EXPOSE 726
 # docker build -t application_iso .
 # docker run -i -t -v ~/Prompta_AI:/Prompta_AI -p 726:726 -w /Prompta_AI/codebase --name application_instance --rm application_iso python main.py
 # docker run -i -t -v ~/Prompta_AI:/Prompta_AI -p 726:726 -w /Prompta_AI/codebase --name application_instance --rm application_iso /bin/bash
