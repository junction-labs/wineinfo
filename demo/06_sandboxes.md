name: my-sandbox
spec:
  labels:
    dev: jane
  cluster: my-cluster
  description: Testing sandboxes
  forks:
  - forkOf:
      kind: Deployment
      namespace: example
      name: my-app
    customizations:
      images:
      - image: example.com/my-app:dev-abcdef
      env:
      - name: EXTRA_ENV
        value: foo
  defaultRouteGroup:
    endpoints:
    - name: my-endpoint       
      target: http://my-app.example.svc:8080

