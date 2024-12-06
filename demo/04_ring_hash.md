# Ring Hash

We all know about sharding, which is taking some parameter of a request, running it through a hash 
function, and then using that to choose consistently across N hosts. Unfortunately sharding has 2 problems,
which Junction Labs aims to solve:
- the first, is now you have that somewhat hacky hashing code to maintain in all of your clients
- this is made worse by the second, which is even if you work out how to load the number N dynamically,
 changing it is really hard as instantaneously every request goes to a completely new host.

## Background

The search team is having problems. Their search data no longer completely fits in memory, meaning
they are seeing massive spikes in response times. They know they eventually need to shard at the storage
layer, but that is a lot of work. For now they just need a way of scaling up.

Enter consistent hashing. Junction implements a consistent hashing algorithm called RingHash,
allowing you to consistently send traffic to the same place as you scale up and down

In unit test mode:

- first scale up to 3 nodes
- show the traffic sprayed across all 3 nodes
- put ring hash in place
- now consistent
- scale up again
- show something else??

In production:

- put in place ring hash
- scale up
- show queries are being served by the same IP.

