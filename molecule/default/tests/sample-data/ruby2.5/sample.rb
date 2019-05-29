require 'json'
require 'rails'

def handler(event:, context:)
  {
    statusCode: 200,
    body: JSON.generate({
      rails: Rails::VERSION::STRING,
    }),
  }
end
