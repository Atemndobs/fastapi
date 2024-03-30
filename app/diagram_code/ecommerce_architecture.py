import os
from diagrams import Diagram, Cluster
from diagrams.aws.compute import EC2
from diagrams.aws.database import RDS
from diagrams.aws.network import ELB
from diagrams.aws.security import IAM
from diagrams.aws.analytics import Kinesis
from diagrams.aws.storage import S3
# from diagrams.aws.management import CloudFormation

def create_diagram(filename, diagram_dir):
    diagram_path = os.path.join(diagram_dir, f'{filename}.png')
    os.makedirs(diagram_dir, exist_ok=True)

    with Diagram(name='Amazon E-Commerce Architecture', show=False, filename=diagram_path, outformat='png'):
        with Cluster('Presentation Layer'):
            user = EC2('User')
            authentication = IAM('User Authentication')
            search = EC2('Product Search')
            shopping_cart = EC2('Shopping Cart')
            payment = EC2('Payment Processing')
            order = EC2('Order Management')
            reviews = EC2('Customer Reviews')
            personalization = EC2('Personalization Algorithms')
            marketing = EC2('Marketing Analytics')

        with Cluster('Application Layer'):
            application = EC2('Application')
            application - [search, shopping_cart, payment, order, reviews, personalization, marketing]

        with Cluster('Data Layer'):
            data = RDS('Database')
            inventory = S3('Inventory Management')

#         with Cluster('International Expansion'):
#             international = CloudFormation('International Expansion Support')

        user >> authentication
        user >> search
        user >> shopping_cart
        user >> payment
        user >> order
        user >> reviews
        user >> personalization
        user >> marketing

        authentication >> application
        search >> application
        shopping_cart >> application
        payment >> application
        order >> application
        reviews >> application
        personalization >> application
        marketing >> application

        application >> data
        application >> inventory

#         application >> international

    return diagram_path
