"""Quick evaluation script for graph metrics."""
import pandas as pd
import networkx as nx

df_c = pd.read_csv('data_output/cureus/concepts.csv')
df_r = pd.read_csv('data_output/cureus/relations.csv')

G = nx.DiGraph()
for _, row in df_c.iterrows():
    G.add_node(row['concept_id'])
for _, row in df_r.iterrows():
    G.add_edge(row['source_id'], row['target_id'], weight=row['weight'])

print('=== GRAPH TOPOLOGY METRICS ===')
print(f'Nodes: {G.number_of_nodes()}')
print(f'Edges: {G.number_of_edges()}')
print(f'Density: {nx.density(G):.4f}')
print(f'Is DAG: {nx.is_directed_acyclic_graph(G)}')

Gu = G.to_undirected()
print(f'Connected components: {nx.number_connected_components(Gu)}')
largest_cc = max(nx.connected_components(Gu), key=len)
print(f'Largest CC size: {len(largest_cc)} ({len(largest_cc)/G.number_of_nodes()*100:.1f}%)')

degrees = [d for n, d in G.degree()]
in_degrees = [d for n, d in G.in_degree()]
out_degrees = [d for n, d in G.out_degree()]
print(f'Avg degree: {sum(degrees)/len(degrees):.2f}')
print(f'Max degree: {max(degrees)}')
print(f'Avg in-degree: {sum(in_degrees)/len(in_degrees):.2f}')
print(f'Avg out-degree: {sum(out_degrees)/len(out_degrees):.2f}')

isolated = list(nx.isolates(G))
print(f'Isolated nodes: {len(isolated)}')

try:
    pr = nx.pagerank(G, weight='weight')
    top5 = sorted(pr.items(), key=lambda x: x[1], reverse=True)[:5]
    top5_names = [(df_c[df_c['concept_id']==nid]['concept_name'].values[0] if len(df_c[df_c['concept_id']==nid])>0 else nid, sc) for nid, sc in top5]
    print(f'Top-5 PageRank nodes: {top5_names}')
except Exception as e:
    print(f'PageRank error: {e}')

try:
    avg_cluster = nx.average_clustering(G.to_undirected())
    print(f'Avg clustering coefficient: {avg_cluster:.4f}')
except Exception as e:
    print(f'Clustering error: {e}')

print('\nData quality checks:')
print(f'Concepts with definitions: {(df_c["definition"].notna() & (df_c["definition"] != "")).sum()} / {len(df_c)}')
print(f'Relations with evidence: {(df_r["evidence"].notna() & (df_r["evidence"] != "")).sum()} / {len(df_r)}')
print(f'Concepts with aliases: {(df_c["aliases"].notna() & (df_c["aliases"] != "")).sum()} / {len(df_c)}')
print(f'Weight range: min={df_r["weight"].min()}, max={df_r["weight"].max()}, mean={df_r["weight"].mean():.2f}')
