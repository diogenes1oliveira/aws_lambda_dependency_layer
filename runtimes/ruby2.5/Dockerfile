FROM lambci/lambda:build-ruby2.5
LABEL maintainer="Diógenes Oliveira <diogenes@rcstecnologia.com.br>"

# Files to be included in the bundle
# Assure to set BUNDLE_GEMFILE=/opt/Gemfile
ENV FILES='ruby/ Gemfile Gemfile.lock .bundle'

WORKDIR /opt/

# Gemfile and Gemfile.lock must be present in the build context
COPY ./Gemfile ./Gemfile.lock ./

# Effectively install the gems
RUN bundle install --deployment --path=.

# Clean up the cache
RUN rm -rf ruby/2.5.0/cache


# Check if the size is smaller than AWS's limits
RUN \
  SIZE=`du -cs $FILES | tail -n 1 | awk '{print $1}'` && \
  test "${SIZE}" -lt 262144000

# Zip it up to /layer.zip
RUN \
  zip -qr layer.zip $FILES && \
  mv layer.zip /layer.zip

ENTRYPOINT [ "/bin/bash" ]
