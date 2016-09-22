# Getting started
Add a `.production.env` file to set the following environmental variable:

`PROJECT_NAME=luuun-nginx`  
`HOST_NAME=luuun-host`  
`ENV_FILE=.production.env`  

Add the luuun server to you ~/.ssh/config file:

>Host luuun-host
>&nbsp;&nbsp;&nbsp;&nbsp;HostName 104.198.0.51  
>&nbsp;&nbsp;&nbsp;&nbsp;Port 45  
>&nbsp;&nbsp;&nbsp;&nbsp;User luuun  
>&nbsp;&nbsp;&nbsp;&nbsp;IdentityFile ~/.ssh/keys/luuun-id-rsa