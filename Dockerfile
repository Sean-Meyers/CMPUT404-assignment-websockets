FROM ubuntu:20.04
RUN apt-get update
RUN apt-get upgrade -y
RUN apt-get install -y python3 python3-dev python3-setuptools python3-pip curl wget git vim locales
RUN pip3 install django flask-sockets==0.2.1 flask==1.1.2 gunicorn requests flask_restful ws4py Werkzeug==1.0.1
RUN echo -e '\n\n\n\n\n\n\n\n' | adduser --disabled-password --quiet me
RUN sed -i -e 's/# en_US.UTF-8 UTF-8/en_US.UTF-8 UTF-8/' /etc/locale.gen && \
    locale-gen
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8     
USER me
WORKDIR /home/me
COPY static ./static
COPY ./*.py .
COPY ./runtests.sh .
COPY ./run.sh .
COPY ./*.txt .
# ADD arb.sh /home/me/arb.sh
# # ADD ../sockets.py /home/me/sockets.py
# # ADD ../runtests.sh /home/me/runtests.sh
# # ADD ../run.sh /home/me/run.sh
# # ADD ../requirements.txt /home/me/requirements.txt
# # ADD ../freetests.py /home/me/freetests.py

# COPY ../*.py .
# COPY ../runtests.sh .
# COPY ../run.sh .
# COPY ../*.txt .
# # WORKDIR /home/me/static
# COPY ../static ./
