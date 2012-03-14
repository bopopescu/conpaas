#!/bin/bash
 
if [ -f /mnt/context.sh ]; then
  . /mnt/context.sh
fi

/sbin/ifconfig eth0 $IP_PUBLIC
/sbin/ip route add default via $IP_GATEWAY
echo "nameserver $NAMESERVER" > /etc/resolv.conf

# fix dns record
grep -q 130.73.121.1 /etc/resolv.conf && echo "nameserver 130.73.79.13" > /etc/resolv.conf

# installation
apt-get update
apt-get install -y unzip python python-mysqldb python-pycurl python-dev python-setuptools python-pip subversion

cd /root
svn co svn://svn.forge.objectweb.org/svnroot/contrail/trunk/conpaas/conpaas-mysql conpaassql
cd conpaassql
python setup.py bdist_egg
easy_install dist/conpaas*
make install

cat > /etc/contrail/conpaas/conpaas-mysql-manager.cnf << EOF
[iaas]
DRIVER=OPENNEBULA_XMLRPC
OPENNEBULA_URL= http://10.30.1.14:2633/RPC2
OPENNEBULA_USER = oneadmin
OPENNEBULA_PASSWORD=oneadmin
OPENNEBULA_IMAGE_ID =  221
OPENNEBULA_SIZE_ID = 1
OPENNEBULA_NETWORK_ID = 205
OPENNEBULA_NETWORK_GATEWAY=$IP_GATEWAY
OPENNEBULA_NETWORK_NAMESERVER=$NAMESERVER

[manager]
find_existing_agents = true
logfile=/var/log/conpaassql-stdout.log
poll_agents_timer=10

[onevm_agent_template]
FILENAME=/usr/share/contrail/conpaas/mysql/agent/agent.template
USERDATA=/usr/share/contrail/conpaas/mysql/agent/init.sh
NAME=conpaassql_server
CPU=0.2
MEM_SIZE=256
DISK=readonly=no
OS=arch=x86_64,boot=hd
IMAGE_ID=221
NETWORK_ID=205
CONTEXT=ip_gateway="$IP_GATEWAY",netmask="$NETMASK",nameserver="$NAMESERVER"
EOF

chmod +x /usr/share/contrail/conpaas/mysql/conpaas-mysql-manager-server
nohup /usr/share/contrail/conpaas/mysql/conpaas-mysql-manager-server ${IP_PUBLIC} 50000 &