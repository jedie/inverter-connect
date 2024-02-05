# builder image
FROM ubuntu:latest AS builder

RUN apt-get update && apt-get install --no-install-recommends -y python3.10 python3.10-dev python3.10-venv python3-pip python3-wheel build-essential && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

# create and activate virtual environment
# using final folder name to avoid path issues with packages
RUN python3 -m venv /home/user/inverter-connect/.venv-app
ENV PATH="/home/user/inverter-connect/.venv-app/bin:$PATH"

# install requirements
COPY requirements.txt .
RUN pip3 install --no-cache-dir wheel
RUN pip3 install --no-cache-dir -r requirements.txt


# runner image
FROM ubuntu:latest AS runner
LABEL Description="inverter-connect"

RUN apt-get update && apt-get install --no-install-recommends -y python3.10 python3.10-venv && \
	apt-get clean && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home user

#USER user
RUN mkdir /home/user/inverter-connect
COPY --from=builder /home/user/inverter-connect/.venv-app /home/user/inverter-connect/.venv-app
WORKDIR /home/user/inverter-connect
COPY . .
RUN chown -R user:user /home/user/inverter-connect

RUN mkdir -p /home/user/.config/inverter-connect
COPY cfg/inverter-connect.toml /home/user/.config/inverter-connect/inverter-connect.toml
RUN chown -R user:user /home/user/.config/inverter-connect

# change user
USER user

# make sure all messages always reach console
#ENV PYTHONUNBUFFERED=1

# activate virtual environment
#ENV VIRTUAL_ENV=/home/user/venv
#ENV PATH="/home/myuser/venv/bin:$PATH"

RUN ./cli.py --help

#CMD ["/bin/bash"]
CMD ["./cli.py", "publish-loop"]
