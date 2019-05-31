# lambda-dependency-layer

Ansible role to build and deploy a Lambda layer bundled with the dependencies
for a given runtime.

## Requirements

Requires `python3.7` and the following PIP libraries to be installed in the
control node:

- `ansible ~= 2.7`
- `boto3 ~= 1.9`
- `docker ~= 4.0`

## Role Variables

| Variable     | Description                              | Default value                      |
| ------------ | ---------------------------------------- | ---------------------------------- |
| `state`      | `absent` or `present`                    | `present`                          |
| `name`       | name of the Lambda layer to be published | (required)                         |
| `runtime`    | valid AWS Lambda runtime                 | `ruby2.5`                          |
| `context`    | path to the build context                | (required if `state == 'present'`) |
| `bucket`     | bucket where to store the resulting ZIP  | (required if `state == 'present'`) |
| `object_key` | key of the ZIP in S3                     | (required if `state == 'present'`) |

The build context must contain the files with the dependencies specifications
for each supported runtime, according to the table below:

| Runtime   | File specs                |
| --------- | ------------------------- |
| `ruby2.5` | `Gemfile`, `Gemfile.lock` |

## Dependencies

The following variables are exported:

| Variable                                | Description                      | Returned when        |
| --------------------------------------- | -------------------------------- | -------------------- |
| aws_lambda_dependency_layer_state       | `absent` or `present`            | always               |
| aws_lambda_dependency_layer_name        | Name of the Lambda layer         | always               |
| aws_lambda_dependency_layer_version     | Published version                | `state == 'present'` |
| aws_lambda_dependency_layer_version_arn | Full ARN of the uploaded version | `state == 'present'` |

## Example Playbook

```yaml
- hosts: localhost
  roles:
    - role: lambda-dependency-layer
      name: my-lambda-ruby-layer
      state: present
      context: .
      runtime: ruby2.5
```

## License

MIT

## Author Information

Diógenes Oliveira - May 2019
