from cassandra.cluster import Cluster
cluster = Cluster(["127.0.0.1"])
cassandra_session = cluster.connect("socialmedia")