FROM debian

MAINTAINER Martin Drohmann <mdrohmann@gmail.com>

ENV LANG en_US.UTF-8
ENV LC_ALL en_US.UTF-8

ENV DEBIAN_FRONTEND noninteractive
RUN echo 'Acquire::http { Proxy "http://192.168.1.137:3142"; };' > /etc/apt/apt.conf.d/02proxy && \
    apt-get update -q && \
    apt-get install --no-install-recommends -qy git-core \
        locales \
        openssh-server \
    && \
    echo $LANG UTF-8 >> /etc/locale.gen && \
    locale-gen $LANG

# To avoid annoying "perl: warning: Setting locale failed." errors,
# do not allow the client to pass custom locals, see:
# http://stackoverflow.com/a/2510548/15677
RUN sed -i 's/^AcceptEnv LANG LC_\*$//g' /etc/ssh/sshd_config

RUN mkdir /var/run/sshd

RUN adduser --system --group --shell /bin/sh git

USER git
WORKDIR /home/git

# initialize home for git user
RUN mkdir bin && \
    git clone --depth=1 git://github.com/sitaramc/gitolite && \
    gitolite/install -ln /home/git/bin && \
    ln -s /repositories repositories

USER root

# https://github.com/docker/docker/issues/5892
RUN chown -R git:git /home/git && \
    # http://stackoverflow.com/questions/22547939/docker-gitlab-container-ssh-git-login-error
    sed -i '/session    required     pam_loginuid.so/d' /etc/pam.d/sshd

COPY ./init.sh /init

# Add volume to repositories directory
VOLUME /repositories

RUN chmod +x /init
CMD ["/init", "/usr/sbin/sshd", "-D"]

EXPOSE 22
