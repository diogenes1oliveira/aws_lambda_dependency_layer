FROM lambci/lambda:build-ruby2.5
LABEL maintainer="Diógenes Oliveira <diogenes@rcstecnologia.com.br>"
ARG name="deployment"

WORKDIR /opt

# Gemfile and Gemfile.lock must be present in the build context
COPY ./Gemfile ./Gemfile.lock ./

# Create the bootstrapping code
# To set up this layer, require 'aws_lambda_dependency_layer_setup/${name}'
RUN \
  mkdir -p 'ruby/lib/aws_lambda_dependency_layer_setup' && \
  echo "require '/opt/ruby/gems/2.5.0/layers/${name}/bundler/setup.rb'" \
  > "ruby/lib/aws_lambda_dependency_layer_setup/${name}.rb"

# Effectively install the gems
RUN \
  bundle install --deployment --standalone --path="ruby/gems/2.5.0/layers/${name}"

# Remove the cache
RUN rm -rf "ruby/gems/2.5.0/layers/${name}/ruby/2.5.0/cache"

# Check if the size is smaller than AWS's limits
RUN \
  SIZE=`du -s ruby | awk '{print $1}'` && \
  test "${SIZE}" -lt 262144000

# Zip it up to /layer.zip
RUN \
  zip -qr layer.zip ruby/ && \
  mv layer.zip /

# Test if I can require the bundler setup
WORKDIR /tmp
RUN \
  ruby -e "require 'aws_lambda_dependency_layer_setup/${name}'"
