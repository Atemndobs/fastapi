from diagrams import Cluster, Diagram, Edge
from diagrams.onprem.analytics import Spark
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.aggregator import Fluentd
from diagrams.onprem.monitoring import Grafana, Prometheus
from diagrams.onprem.network import Nginx
from diagrams.onprem.queue import Kafka
import os

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB
from diagrams.aws.storage import S3
from diagrams.onprem.client import Users
from diagrams.onprem.compute import Server
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.network import Internet

def create_diagram(filename, diagram_dir):
    diagram_path = os.path.join(diagram_dir, f'{filename}.png')
    diagram_dir = os.path.join(os.path.dirname(__file__), '../diagrams')
    os.makedirs(diagram_dir, exist_ok=True)
    diagram_path = os.path.join(diagram_dir, filename)

    with Diagram(name='Advanced Web Service with On-Premise (colored)', show=False, filename=diagram_path, outformat='png'):
        with Cluster("AWS Cloud"):
            with Cluster("Web Servers"):
                web_servers = [EC2("Web Server 1"), EC2("Web Server 2"), EC2("Web Server 3")]

            with Cluster("Load Balancer"):
                lb = ELB("ELB")
                lb >> Edge(label="distributes traffic") >> web_servers

            with Cluster("Static Content"):
                static_content = S3("Static Charts")

            with Cluster("Dynamic Content"):
                dynamic_content = EC2("Dynamic Charts")

            with Cluster("Database"):
                db = RDS("Ratings Database")
                web_servers >> Edge(label="connects to") >> db

        internet = Internet("Internet")
        artists = Users("Artists/Labels")
        djs = Users("DJs")
        admin_users = Users("Admin Users")

        internet >> artists >> lb
        internet >> djs >> lb
        internet >> admin_users >> lb

        web_servers >> Edge(label="updates") >> static_content
        web_servers >> Edge(label="updates") >> dynamic_content

        artists >> Edge(label="upload songs to") >> static_content
        djs >> Edge(label="rate songs in") >> dynamic_content
        admin_users >> dynamic_content

        dynamic_content >> Edge(label="syncs on Sunday") >> static_content
        db >> Edge(label="stores") >> [static_content, dynamic_content]