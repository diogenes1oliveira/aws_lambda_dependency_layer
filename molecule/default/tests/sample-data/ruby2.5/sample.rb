# frozen_string_literal: true

require 'bundler/setup'
require 'json'
require 'rails'
require 'sinatra'

def handler(event:, context:)
  {
    statusCode: 200,
    body: JSON.generate(
      rails: Rails::VERSION::STRING,
      sinatra: Sinatra::VERSION
    )
  }
end
