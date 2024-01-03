# Use an official Elasticsearch image as the base image
FROM docker.elastic.co/elasticsearch/elasticsearch:7.10.0

# Set the cluster name
ENV cluster.name=movirama-cluster

# Set the node name
ENV node.name=movirama-node

ENV network.host=_site_
ENV http.publish_host=_site_

ENV cluster.routing.allocation.enable=all
ENV cluster.routing.allocation.node_concurrent_recoveries=2
# ENV xpack.security.enabled=true
# ENV xpack.security.transport.ssl.enabled=true

# # Copy custom configuration files
# COPY elasticsearch.yml /usr/share/elasticsearch/config/

# Run Elasticsearch in the foreground
CMD ["elasticsearch"]
