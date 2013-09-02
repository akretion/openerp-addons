#!/usr/bin/env bash

cd ../server

./openerp-server --db_user=postgres --db_user=openerp --db_password=admin --db_host=localhost --stop-after-init --addons-path=../openerp-addons,../web/addons -i sale,purchase,stock,crm,project -d rsocb > >(tee stdout.log)

if $(grep -v mail stdout.log | grep -q ERROR)
then
exit 1
else
exit 0
fi
