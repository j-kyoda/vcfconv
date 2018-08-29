vcfconv
==========

Convert vCard(*.vcf) to your LDAP ldif for address book

Required
--------

* python3.6.x

How to use
----------

* Convert vCard(*.vcf) to LDAP ldif.

	vcfldifconv.py -b YOUR_LDAP_BASE_PATH -f VCF_FILE

example operation
-----------------

	$ python vcfconv.py -b ou=account,ou=Address,dc=example,dc=com -f contacts.vcf > contacts.ldif
	$ ldapadd -x -D uid=account,ou=People,dc=example,dc=com -W -f contacts.ldif
