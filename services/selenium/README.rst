Selenium Hub
============

1. Start the hub

   ::

      docker run -d -p 4444:4444 --name selenium-hub selenium/hub

2. Start the client(s)

   ::

      docker run -d -P --link selenium-hub:hub --name=firefox-node -v /tmp/e2e/uploads:/e2e/uploads selenium/node-firefox-debug
      docker run -d -P --link selenium-hub:hub --name=chrome-node -v /tmp/e2e/uploads:/e2e/uploads selenium/node-chrome-debug

   Alternatively source the ``source`` file to get aliases for temporary
   containers, that can be started with `FF` or `CH`

3. For debugging purposes, inspect

   ::

      docker port firefox-node 5900

   and start the vnc viewer

   ::

      xvnc4viewer localhost:port

   the password is `secret`.

