// Independent graph-level checker. Safety labels are supplied by the model exporter.
// Progress uses Kahn cycle elimination, rather than the Python AF fixed point.
#include <iostream>
#include <fstream>
#include <vector>
#include <queue>
#include <stdexcept>
int main(int argc,char**argv){
 try{
  if(argc!=2)throw std::runtime_error("usage: checker graph.txt");
  std::ifstream in(argv[1]); size_t n,m; if(!(in>>n>>m)||!n)throw std::runtime_error("bad header");
  std::vector<int> terminal(n),mask(n),degree(n);std::vector<std::vector<size_t>> g(n);
  for(size_t i=0;i<n;i++)if(!(in>>terminal[i]>>mask[i]))throw std::runtime_error("bad labels");
  for(size_t i=0,u,v;i<m;i++){if(!(in>>u>>v)||u>=n||v>=n)throw std::runtime_error("bad edge");g[u].push_back(v);}
  std::vector<bool> reached(n,false);std::queue<size_t> q;q.push(0);reached[0]=true;size_t count=0;int safety=0;
  while(!q.empty()){auto u=q.front();q.pop();count++;safety|=mask[u];if(g[u].empty())throw std::runtime_error("graph not totalized");for(auto v:g[u]){if(terminal[u]&&v!=u)throw std::runtime_error("terminal not absorbing");if(!reached[v]){reached[v]=true;q.push(v);}}}
  size_t active=0,removed=0;
  for(size_t u=0;u<n;u++)if(reached[u]&&!terminal[u]){active++;for(auto v:g[u])if(reached[v]&&!terminal[v])degree[v]++;}
  for(size_t u=0;u<n;u++)if(reached[u]&&!terminal[u]&&!degree[u])q.push(u);
  while(!q.empty()){auto u=q.front();q.pop();removed++;for(auto v:g[u])if(reached[v]&&!terminal[v]&&!--degree[v])q.push(v);}
  if(active!=removed)safety|=1<<3;
  std::cout<<"{\"reachable\":"<<count<<",\"edges\":"<<m<<",\"violation_mask\":"<<safety<<",\"nonterminal_cycle\":"<<(active!=removed?"true":"false")<<"}\n";
 }catch(const std::exception&e){std::cerr<<e.what()<<"\n";return 2;}
}
