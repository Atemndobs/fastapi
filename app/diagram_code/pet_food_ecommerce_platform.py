import os
from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB
from diagrams.onprem.client import Users
from diagrams.onprem.inmemory import Redis
from diagrams.onprem.queue import Kafka
from diagrams.saas.recommendation import Recombee
from diagrams.saas.social import Twitter

def create_diagram(filename, diagram_dir):
    diagram_path = os.path.join(diagram_dir, f'{filename}')
    os.makedirs(diagram_dir, exist_ok=True)

    with Diagram(name='Pet Food E-commerce Platform', show=False, filename=diagram_path, outformat='png'):
        with Cluster('Core Platform'):
            users = Users('customers')
            magento = EC2('Magento')
            vuefront = EC2('Vue Storefront')
            db = RDS('Database')

            users >> magento >> db
            users >> vuefront >> db

        with Cluster('Auxiliary Services'):
            auth = EC2('User Auth')
            payment = EC2('Payment Processing')
            shipping = EC2('Shipping Calculation')
            reviews = EC2('Customer Reviews')

            magento >> auth
            magento >> payment
            magento >> shipping
            magento >> reviews

        with Cluster('Marketing & Analytics'):
            email_marketing = Recombee('Email Marketing')
            analytics = Kafka('Analytics')
            seo = EC2('SEO Optimization')
            social = Twitter('Social Media')

            magento >> email_marketing
            magento >> analytics
            vuefront >> seo
            vuefront >> social

            cache = Redis('Cache')
            magento >> cache
            vuefront >> cache

    return diagram_path