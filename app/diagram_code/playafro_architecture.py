from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB
from diagrams.aws.storage import S3
from diagrams.onprem.client import Users
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.network import Internet

with Diagram('PlayAfro Music Rating Platform', show=False, filename='playafro_architecture', outformat='png'):
    with Cluster('AWS Cloud'):
        with Cluster('Web Servers'):
            web_servers = [EC2('Web Server 1'), EC2('Web Server 2'), EC2('Web Server 3')]
        with Cluster('Load Balancer'):
            lb = ELB('ELB')
            lb >> Edge(label='distributes traffic') >> web_servers
        with Cluster('Static Content'):
            static_content = S3('Static Charts')
        with Cluster('Dynamic Content'):
            dynamic_content = EC2('Dynamic Charts')
        with Cluster('Database'):
            db = RDS('Ratings Database')
            web_servers >> Edge(label='connects to') >> db

    internet = Internet('Internet')
    artists_labels = Users('Artists/Labels')
    djs = Users('DJs')
    admin_users = Users('Admin Users')

    internet >> artists_labels >> lb
    internet >> djs >> lb
    internet >> admin_users >> lb

    web_servers >> Edge(label='updates') >> static_content
    web_servers >> Edge(label='updates') >> dynamic_content

    artists_labels >> Edge(label='upload songs to') >> static_content
    djs >> Edge(label='rate songs in') >> dynamic_content
    admin_users >> dynamic_content

    dynamic_content >> Edge(label='syncs on Sunday') >> static_content
    db >> Edge(label='stores') >> [static_content, dynamic_content]