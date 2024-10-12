# Создать пароль для внешних приложений 
https://help.mail.ru/mail/security/protection/external/

Monitoring Metricbeat 

http://localhost:5601/app/monitoring


## Создать юзера

```
curl -u elastic:changeme -X POST "http://localhost:9200/_security/user/kibana_system" -H "Content-Type: application/json" -d '{
  "password" : "changeme",
  "roles" : [ "kibana_system" ],
  "full_name" : "Kibana System User",
  "metadata" : { }
}'
```

## Сменить пароль юзера
```
curl -u elastic:changeme -X PUT "http://localhost:9200/_security/user/kibana_system/_password" -H "Content-Type: application/json" -d '{
  "password" : "changeme"
}'
```

###   Создать ключ http://localhost:5601/app/management/security/api_keys/create