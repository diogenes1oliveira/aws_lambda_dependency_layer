FROM lambci/lambda:build-ruby2.5
LABEL maintainer="Diógenes Oliveira <diogenes@rcstecnologia.com.br>"

WORKDIR /var/layer

# Gemfile and Gemfile.lock must be present in the build context
COPY ./Gemfile ./Gemfile.lock ./

# Effectively install the gems
RUN bundle install --path=ruby/gems && \
    mv ruby/gems/ruby/* ruby/gems/ && \
    rm -rf ruby/gems/2.5.0/cache ruby/gems/ruby

# Assure the uncompressed size is below AWS's limits
RUN SIZE=`du -s ruby | awk '{print $1}'` && \
    test "${SIZE}" -lt 262144000 

# Zip and clean up
RUN rm -f layer.zip && \
    zip -qr layer.zip ruby && \
    mv layer.zip /layer.zip && \
    rm -rf .bundle ruby
