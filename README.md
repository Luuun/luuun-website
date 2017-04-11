ZapGo Website
=============
Automated Deployment:
-----------------
TODO

Manual Deployment:
------------------
### Push to container registry:
1. Build the static webserver:  
   `inv build -c production -v v0.001`
2. Push to Container Registry:  
   `inv build -c production -v v0.001`
3. Run locally:
    `inv run -c production -v v0.001`
4. Deploy to Kubernetes Cluster:
    `inv deploy -c production.yaml -v v0.001`

### Once-off Kubernetes Cluster Setup:
1. Create a Kubernetes Cluster
2. Athenticate gcloud:    
    `gcloud auth login`  
    `gcloud config set project {project-name}`  
3. Connect to kubernetes cluster:  
    `gcloud container clusters get-credentials hosting-cluster --zone us-west1-a --project {project-name}`  
4. Letsencrypt SSL setup:  
    `kubectl apply -f lego/00-namespace.yaml && kubectl apply -f lego/configmap.yaml && kubectl apply -f lego/deployment.yaml`  
5. Webserver setup:  
    `inv templater production.yaml`  
	`kubectl apply -f server/kubernetes/production/all-in-one.yaml`  
6. Check the external IP address and setup DNS:  
   `kubectl get ingress --namespace luuun-website luuun-website`  