FROM ubuntu:16.04

ENV TERM XTerm

RUN apt-get update
RUN apt-get install -y wget


### ROOT
WORKDIR /usr/opt/

RUN wget https://root.cern.ch/download/root_v6.12.06.Linux-ubuntu16-x86_64-gcc5.4.tar.gz
RUN tar xvfz root_v6.12.06.Linux-ubuntu16-x86_64-gcc5.4.tar.gz
WORKDIR /usr/opt/root

RUN apt-get install -y apt-utils cmake
RUN apt-get install -y libtbb2 g++ gcc
RUN apt-get install -y python
RUN apt-get install -y make
RUN apt-get install -y python-dev

RUN apt-get update
RUN apt-get upgrade -y binutils

### GEANT
WORKDIR /usr/opt

RUN wget http://geant4.web.cern.ch/geant4/support/source/geant4.10.01.p03.tar.gz
RUN tar -xzf geant4.10.01.p03.tar.gz

WORKDIR /usr/opt/geant_build

RUN cmake -DCMAKE_INSTALL_PREFIX=/usr/opt/geant -DGEANT4_INSTALL_DATA=ON -DBUILD_SHARED_LIBS=ON /usr/opt/geant4.10.01.p03/
RUN make -j8
RUN make install
RUN rm -rf /usr/opt/geant_build

### Python

RUN apt-get update
RUN apt-get install -y python-pip

RUN pip install numpy

### CRAYFIS-SIM

COPY data /usr/app/data
COPY include /usr/app/include
COPY src /usr/app/src
COPY scripts /usr/app/scripts
COPY GNUmakefile /usr/app/
COPY TestEm1.cc /usr/app/

WORKDIR /usr/app/

RUN bash -c "export G4INSTALL=/usr/opt/geant/ && source /usr/opt/root/bin/thisroot.sh && source /usr/opt/geant/share/Geant4-10.1.3/geant4make/geant4make.sh && export G4G4WORKDIR=/usr/geant_workdir && make -j9"

WORKDIR /usr/app/
RUN bash -c "source /usr/opt/root/bin/thisroot.sh && python scripts/configs.py 1000000 -n 3000 -j1000 -o /output"

COPY run.sh /usr/app/
COPY run.py /usr/app/

CMD sh run.sh