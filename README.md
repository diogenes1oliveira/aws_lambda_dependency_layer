# lambda-dependency-layer

Ansible role to build and deploy a Lambda layer bundled with the dependencies
for a given runtime.

## Requirements

Requires `python3.7` and the following PIP libraries to be installed in the
control node:

- ansible ~= 2.7
- boto3 ~= 1.9
- docker ~= 4.0

## Role Variables

| Variable   | Description                              | Default value |
| ---------- | ---------------------------------------- | ------------- |
| state      | `absent` or `present`                    | `present`     |
| name       | name of the Lambda layer to be published | (required)    |
| runtime    | valid AWS Lambda runtime                 | `ruby2.5`     |
| context    | path to the build context                | (required)    |
| bucket     | bucket where to store the resulting ZIP  | (required)    |
| object_key | key of the ZIP in S3                     | (required)    |

The build context must contain the files with the dependencies specifications
for each runtime, according to the table below:

| Runtime   | File specs                |
| --------- | ------------------------- |
| `ruby2.5` | `Gemfile`, `Gemfile.lock` |

## Dependencies

The following variables are exported:

| Variable                            | Description                      |
| ----------------------------------- | -------------------------------- |
| lambda_dependency_layer_name        | Name of the Lambda layer         |
| lambda_dependency_layer_arn         | ARN of the Lambda layer          |
| lambda_dependency_layer_version     | Published version                |
| lambda_dependency_layer_version_arn | Full ARN of the uploaded version |

## Example Playbook

```yaml
- hosts: localhost
  roles:
    - role: lambda-dependency-layer
      path: .
      runtime: ruby2.5
```

## License

MIT

## Author Information

Diógenes Oliveira - May 2019
