# GitHub Actions -> AWS App Runner (No Existing Repo)

This guide sets up automatic deployment from GitHub to AWS App Runner.

## 1) Create a GitHub repository and push code

```bash
git init
git add .
git commit -m "Initial FastAPI app with CI/CD"
git branch -M main

# Option A: GitHub CLI
gh repo create wordcount-api --public --source=. --remote=origin --push

# Option B: create repo in GitHub UI, then:
# git remote add origin git@github.com:<your-user>/wordcount-api.git
# git push -u origin main
```

## 2) In AWS, create ECR repositories

Use your AWS region and desired repository names.

```bash
aws ecr create-repository --repository-name wordcount-api --region us-east-1
aws ecr create-repository --repository-name wordcount-frontend --region us-east-1
```

If it already exists, this command can fail safely and be ignored.

## 3) Create App Runner ECR access role

App Runner needs a role to pull private ECR images.

Use the included trust policy template:

- `aws/iam/apprunner-ecr-trust.json`

Create role and attach AWS managed policy:

```bash
aws iam create-role \
  --role-name AppRunnerECRAccessRole \
  --assume-role-policy-document file://aws/iam/apprunner-ecr-trust.json

aws iam attach-role-policy \
  --role-name AppRunnerECRAccessRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
```

Capture role ARN:

```bash
aws iam get-role --role-name AppRunnerECRAccessRole --query Role.Arn --output text
```

## 4) Create GitHub OIDC deployment role in AWS

This role is assumed by GitHub Actions and should have permissions for ECR and App Runner.

Use these included templates and replace placeholders first:

- `aws/iam/github-oidc-trust.json`
- `aws/iam/github-deploy-policy.json`

Create the role and inline policy:

```bash
aws iam create-role \
  --role-name GitHubActionsAppRunnerDeployRole \
  --assume-role-policy-document file://aws/iam/github-oidc-trust.json

aws iam put-role-policy \
  --role-name GitHubActionsAppRunnerDeployRole \
  --policy-name GitHubActionsAppRunnerDeployPolicy \
  --policy-document file://aws/iam/github-deploy-policy.json
```

Save this role ARN; you will add it as a GitHub secret.

## 5) Configure repository variables and secrets in GitHub

In GitHub repo settings:

Repository Variables:
- `AWS_REGION` = `us-east-1`
- `ECR_REPOSITORY_API` = `wordcount-api`
- `ECR_REPOSITORY_FRONTEND` = `wordcount-frontend`
- `SERVICE_NAME_API` = `wordcount-api`
- `SERVICE_NAME_FRONTEND` = `wordcount-frontend`

Repository Secrets:
- `AWS_DEPLOY_ROLE_ARN` = ARN of GitHub OIDC deployment role
- `APPRUNNER_ECR_ACCESS_ROLE_ARN` = ARN of `AppRunnerECRAccessRole`

## 6) Trigger deployment

Push to `main` branch or run workflow manually from GitHub Actions tab.

Workflow file:
- `.github/workflows/deploy.yml`

## 7) Verify deployment

After workflow completes, check logs for both App Runner URLs:

- API: `https://<api-service-url>/docs`
- Frontend: `https://<frontend-service-url>`
- Upload multiple files from the Streamlit UI and verify returned filename/extension/word_count metadata.

## Notes

- This pipeline uses AWS SDK (boto3) in `scripts/deploy_apprunner.py` to create or update both App Runner services.
- Frontend deployment injects `API_BASE_URL` as a runtime environment variable so Streamlit can call the API service.
- For production, narrow IAM permissions as much as possible.
