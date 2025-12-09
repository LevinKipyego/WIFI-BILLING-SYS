import os
from dotenv import load_dotenv
import logging
import mysql.connector

# Load environment variables
load_dotenv()

# -------------------------
# DB CONFIG (use env or defaults)
# -------------------------
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "127.0.0.1"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASS", ""),
    "database": os.getenv("DB_NAME", "BILLING"),
    "autocommit": False
}

def get_connection():
    """Get a new database connection."""
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn



#_______DEF QUERY_COUNT_________________##
def update_query_count(tx_uid):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE user_transactions
        SET query_count = query_count + 1
        WHERE transaction_uuid = %s
    """, (tx_uid,))
    conn.commit()
    cursor.close()
    conn.close()



def test():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM user_transactions WHERE status = 'failed'")
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    if result:
        return result
    return None
test()

def test2():
    data = test()
    if data:
      
        for x in data:
            
            update_query_count(x['transaction_uuid'])
            print(f"Updated query count for transaction UUID: {x['transaction_uuid']}")
    return None
test2()
'''
def init_db():
    """Create tables if they don't exist (safe to run multiple times)."""
    conn = get_connection()
    cursor = conn.cursor()
    # Create plans table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_plans (
      id INT AUTO_INCREMENT PRIMARY KEY,
      name VARCHAR(128),
      price DECIMAL(10,2),
      duration_minutes INT,
      mikrotik_profile VARCHAR(128),
      rate_limit VARCHAR(64),
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    # Transactions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_transactions (
      id INT AUTO_INCREMENT PRIMARY KEY,
      transaction_uuid VARCHAR(64) UNIQUE,
      client_phone VARCHAR(32),
      plan_id INT,
      amount DECIMAL(10,2),
      status ENUM('pending','success','failed','processing') DEFAULT 'pending',
      merchant_request_id VARCHAR(128),
      checkout_request_id VARCHAR(128),
      mpesa_receipt VARCHAR(64),
      mac VARCHAR(64),
      ip VARCHAR(64),
      username VARCHAR(128),
      sessionid VARCHAR(128),
      callback_received_at DATETIME NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME NULL,
      expires_at DATETIME NULL
    );
    """)
    # Hotspot users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hotspot_users (
      id INT AUTO_INCREMENT PRIMARY KEY,
      transaction_uuid VARCHAR(64),
      mac VARCHAR(64),
      username VARCHAR(128),
      mikrotik_profile VARCHAR(128),
      expires_at DATETIME,
      active TINYINT(1) DEFAULT 1,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)
    conn.commit()
    cursor.close()
    conn.close()

init_db()
'''
'''
-- --------------------------------------------
-- RADIUS CORE TABLES (MySQL — FreeRADIUS style)
-- --------------------------------------------

CREATE TABLE IF NOT EXISTS radcheck (
    id int(11) unsigned NOT NULL auto_increment,
    username varchar(64) NOT NULL default '',
    attribute varchar(64)  NOT NULL default '',
    op char(2) NOT NULL DEFAULT '==',
    value varchar(253) NOT NULL default '',
    PRIMARY KEY (id),
    KEY username (username)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS radreply (
    id int(11) unsigned NOT NULL auto_increment,
    username varchar(64) NOT NULL default '',
    attribute varchar(64) NOT NULL default '',
    op char(2) NOT NULL DEFAULT '=',
    value varchar(253) NOT NULL default '',
    PRIMARY KEY (id),
    KEY username (username)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS radusergroup (
    id int(11) unsigned NOT NULL auto_increment,
    username varchar(64) NOT NULL default '',
    groupname varchar(64) NOT NULL default '',
    priority int(11) NOT NULL default '1',
    PRIMARY KEY (id),
    KEY username (username)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS usergroup (
    username varchar(64) NOT NULL default '',
    groupname varchar(64) NOT NULL default '',
    PRIMARY KEY (username, groupname)
) ENGINE=InnoDB;

-- -------------------------
-- NAS ROUTERS / Mikrotik
-- -------------------------
CREATE TABLE IF NOT EXISTS nas (
    id int(10) NOT NULL auto_increment,
    nasname varchar(128) NOT NULL,
    shortname varchar(32),
    type varchar(30) DEFAULT 'other',
    ports int(5),
    secret varchar(60) NOT NULL,
    server varchar(64),
    community varchar(50),
    description varchar(200),
    PRIMARY KEY (id)
) ENGINE=InnoDB;

-- -------------------------
-- ACCOUNTING (radacct)
-- -------------------------
CREATE TABLE IF NOT EXISTS radacct (
    radacctid bigint(21) NOT NULL auto_increment,
    acctsessionid varchar(64) NOT NULL default '',
    acctuniqueid varchar(32) NOT NULL default '',
    username varchar(64) NOT NULL default '',
    realm varchar(64) default '',
    nasipaddress varchar(15) NOT NULL default '',
    nasportid varchar(15) default NULL,
    nasporttype varchar(32) default NULL,
    acctstarttime datetime default NULL,
    acctupdatetime datetime default NULL,
    acctstoptime datetime default NULL,
    acctsessiontime int(12) default NULL,
    acctauthentic varchar(32) default NULL,
    connectinfo_start varchar(50) default NULL,
    connectinfo_stop varchar(50) default NULL,
    acctinputoctets bigint(20) default NULL,
    acctoutputoctets bigint(20) default NULL,
    calledstationid varchar(50) NOT NULL default '',
    callingstationid varchar(50) NOT NULL default '',
    acctterminatecause varchar(32) NOT NULL default '',
    servicetype varchar(32) default NULL,
    framedprotocol varchar(32) default NULL,
    framedipaddress varchar(15) NOT NULL default '',
    framedipv6address varchar(45) default NULL,
    framedipv6prefix varchar(45) default NULL,
    framedinterfaceid varchar(45) default NULL,
    delegatedipv6prefix varchar(45) default NULL,
    PRIMARY KEY (radacctid),
    KEY acctsessionid (acctsessionid),
    KEY acctuniqueid (acctuniqueid),
    KEY username (username),
    KEY framedipaddress (framedipaddress)
) ENGINE=InnoDB;

-- -------------------------
-- Post-auth table
-- -------------------------
CREATE TABLE IF NOT EXISTS radpostauth (
    id int(11) NOT NULL auto_increment,
    username varchar(64) NOT NULL default '',
    pass varchar(64) NOT NULL default '',
    reply varchar(32) NOT NULL default '',
    authdate timestamp NOT NULL default CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

-- -------------------------------------------
-- SESSION LIMITING (control multi-device use)
-- -------------------------------------------
CREATE TABLE IF NOT EXISTS radgroupreply (
    id int(11) unsigned NOT NULL auto_increment,
    groupname varchar(64) NOT NULL default '',
    attribute varchar(64) NOT NULL default '',
    op char(2) NOT NULL default '=',
    value varchar(253) NOT NULL default '',
    PRIMARY KEY (id),
    KEY groupname (groupname)
) ENGINE=InnoDB;

-- -----------------------------------------
-- Optional table for storing plan durations
-- -----------------------------------------
CREATE TABLE IF NOT EXISTS radius_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_name VARCHAR(100),
    rate_limit VARCHAR(100),
    duration_minutes INT,
    mikrotik_profile VARCHAR(100)
) ENGINE=InnoDB;

'''



'''

###########################################################################
# $Id: 84846b20c93e92ba785a9f9e49375246309b48b9 $                 #
#                                                                         #
#  schema.sql                       rlm_sql - FreeRADIUS SQL Module       #
#                                                                         #
#     Database schema for MySQL rlm_sql module                            #
#                                                                         #
#     To load:                                                            #
#         mysql -uroot -prootpass radius < schema.sql                     #
#                                                                         #
#                                   Mike Machado <mike@innercite.com>     #
###########################################################################
#
# Table structure for table 'radacct'
#

CREATE TABLE IF NOT EXISTS radacct (
  radacctid bigint(21) NOT NULL auto_increment,
  acctsessionid varchar(64) NOT NULL default '',
  acctuniqueid varchar(32) NOT NULL default '',
  username varchar(64) NOT NULL default '',
  realm varchar(64) default '',
  nasipaddress varchar(15) NOT NULL default '',
  nasportid varchar(32) default NULL,
  nasporttype varchar(32) default NULL,
  acctstarttime datetime NULL default NULL,
  acctupdatetime datetime NULL default NULL,
  acctstoptime datetime NULL default NULL,
  acctinterval int(12) default NULL,
  acctsessiontime int(12) unsigned default NULL,
  acctauthentic varchar(32) default NULL,
  connectinfo_start varchar(128) default NULL,
  connectinfo_stop varchar(128) default NULL,
  acctinputoctets bigint(20) default NULL,
  acctoutputoctets bigint(20) default NULL,
  calledstationid varchar(50) NOT NULL default '',
  callingstationid varchar(50) NOT NULL default '',
  acctterminatecause varchar(32) NOT NULL default '',
  servicetype varchar(32) default NULL,
  framedprotocol varchar(32) default NULL,
  framedipaddress varchar(15) NOT NULL default '',
  framedipv6address varchar(45) NOT NULL default '',
  framedipv6prefix varchar(45) NOT NULL default '',
  framedinterfaceid varchar(44) NOT NULL default '',
  delegatedipv6prefix varchar(45) NOT NULL default '',
  class varchar(64) default NULL,
  PRIMARY KEY (radacctid),
  UNIQUE KEY acctuniqueid (acctuniqueid),
  KEY username (username),
  KEY framedipaddress (framedipaddress),
  KEY framedipv6address (framedipv6address),
  KEY framedipv6prefix (framedipv6prefix),
  KEY framedinterfaceid (framedinterfaceid),
  KEY delegatedipv6prefix (delegatedipv6prefix),
  KEY acctsessionid (acctsessionid),
  KEY acctsessiontime (acctsessiontime),
  KEY acctstarttime (acctstarttime),
  KEY acctinterval (acctinterval),
  KEY acctstoptime (acctstoptime),
  KEY nasipaddress (nasipaddress),
  KEY class (class)
) ENGINE = INNODB;

#
# Table structure for table 'radcheck'
#

CREATE TABLE IF NOT EXISTS radcheck (
  id int(11) unsigned NOT NULL auto_increment,
  username varchar(64) NOT NULL default '',
  attribute varchar(64)  NOT NULL default '',
  op char(2) NOT NULL DEFAULT '==',
  value varchar(253) NOT NULL default '',
  PRIMARY KEY  (id),
  KEY username (username(32))
);

#
# Table structure for table 'radgroupcheck'
#

CREATE TABLE IF NOT EXISTS radgroupcheck (
  id int(11) unsigned NOT NULL auto_increment,
  groupname varchar(64) NOT NULL default '',
  attribute varchar(64)  NOT NULL default '',
  op char(2) NOT NULL DEFAULT '==',
  value varchar(253)  NOT NULL default '',
  PRIMARY KEY  (id),
  KEY groupname (groupname(32))
);

#
# Table structure for table 'radgroupreply'
#

CREATE TABLE IF NOT EXISTS radgroupreply (
  id int(11) unsigned NOT NULL auto_increment,
  groupname varchar(64) NOT NULL default '',
  attribute varchar(64)  NOT NULL default '',
  op char(2) NOT NULL DEFAULT '=',
  value varchar(253)  NOT NULL default '',
  PRIMARY KEY  (id),
  KEY groupname (groupname(32))
);

#
# Table structure for table 'radreply'
#

CREATE TABLE IF NOT EXISTS radreply (
  id int(11) unsigned NOT NULL auto_increment,
  username varchar(64) NOT NULL default '',
  attribute varchar(64) NOT NULL default '',
  op char(2) NOT NULL DEFAULT '=',
  value varchar(253) NOT NULL default '',
  PRIMARY KEY  (id),
  KEY username (username(32))
);


#
# Table structure for table 'radusergroup'
#

CREATE TABLE IF NOT EXISTS radusergroup (
  id int(11) unsigned NOT NULL auto_increment,
  username varchar(64) NOT NULL default '',
  groupname varchar(64) NOT NULL default '',
  priority int(11) NOT NULL default '1',
  PRIMARY KEY  (id),
  KEY username (username(32))
);

#
# Table structure for table 'radpostauth'
#
# Note: MySQL versions since 5.6.4 support fractional precision timestamps
#        which we use here. Replace the authdate definition with the following
#        if your software is too old:
#
#   authdate timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
#
CREATE TABLE IF NOT EXISTS radpostauth (
  id int(11) NOT NULL auto_increment,
  username varchar(64) NOT NULL default '',
  pass varchar(64) NOT NULL default '',
  reply varchar(32) NOT NULL default '',
  authdate timestamp(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  class varchar(64) default NULL,
  PRIMARY KEY  (id),
  KEY username (username),
  KEY class (class)
) ENGINE = INNODB;

#
# Table structure for table 'nas'
#
CREATE TABLE IF NOT EXISTS nas (
  id int(10) NOT NULL auto_increment,
  nasname varchar(128) NOT NULL,
  shortname varchar(32),
  type varchar(30) DEFAULT 'other',
  ports int(5),
  secret varchar(60) DEFAULT 'secret' NOT NULL,
  server varchar(64),
  community varchar(50),
  description varchar(200) DEFAULT 'RADIUS Client',
  PRIMARY KEY (id),
  KEY nasname (nasname)
) ENGINE = INNODB;

#
# Table structure for table 'nasreload'
#
CREATE TABLE IF NOT EXISTS nasreload (
  nasipaddress varchar(15) NOT NULL,
  reloadtime datetime NOT NULL,
  PRIMARY KEY (nasipaddress)
) ENGINE = INNODB;
'''