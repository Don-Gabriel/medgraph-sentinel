# Neo4j 5.26 LTS with GDS 2.13 baked in at BUILD time (ADR-026).
#
# Why not NEO4J_PLUGINS: that mechanism downloads the jar from
# graphdatascience.ninja at EVERY container creation — observed live at the
# M1 run on 2026-07-30. The demo venue is offline (ADR-019), so the plugin
# must live in the image the USB tarball carries, not in a runtime download.
# The jar version below is exactly what the official resolver selected for
# neo4j 5.26 (from the container log), satisfying the ADR-004 pairing;
# the M1 gate `RETURN gds.version()` must still report 2.13.x.
FROM neo4j:5.26-community

RUN wget --tries=10 --timeout=60 --continue \
      -O /var/lib/neo4j/plugins/graph-data-science.jar \
      https://graphdatascience.ninja/neo4j-graph-data-science-2.13.11.jar
