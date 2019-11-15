#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Webotron: Deploy websites with aws.

Webotron automates the process of deploying static websites to AWS.
- Configure AWS s3 list_buckets:
    - Create them
    - Set them up for static website hosting
    - Deploy local files to them
- Configure DNS with Route 53
- Configure a Content Delivery Network and SSL with AWS cloudfront
"""

from pathlib import Path
import mimetypes

import boto3
from botocore.exceptions import ClientError

import click


SESSION = boto3.Session(profile_name='pythonAutomation')
S3 = SESSION.resource('s3')


@click.group()
def cli():
    """Webotron deploys websites to AWS."""


@cli.command('list-buckets')
def list_buckets():
    """List all s3 buckets."""
    for bucket in S3.buckets.all():
        print(bucket)


@cli.command('list-bucket-objects')
@click.argument('bucket')
def list_bucket_objects(bucket):
    """List objects in an s3 bucket."""
    for obj in S3.bucket(bucket).objects.all():
        print(obj)


@cli.command('setup-bucket')
@click.argument('bucket')
def setup_bucket(bucket):
    """Create and configure s3 bucket."""
    s3_bucket = None

    try:
        s3_bucket = S3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={
                'LocationConstraint': SESSION.region_name
            })
    except ClientError as error:
        if error.response['Error']['Code'] == 'BucketAlreadyOwnedByYou':
            s3_bucket = S3.Bucket(bucket)
        else:
            raise error

    policy = """
    {
     "Version":"2012-10-17",
     "Statement":[{
     "Sid":"PublicReadGetObject",
     "Effect":"Allow",
     "Principal": "*",
          "Action":["s3:GetObject"],
          "Resource":["arn:aws:s3:::%s/*"
          ]
        }
      ]
    }
    """ % s3_bucket.name

    policy = policy.strip()
    pol = s3_bucket.Policy()
    pol.put(Policy=policy)

    s3_bucket.Website().put(WebsiteConfiguration={
        'ErrorDocument': {
            'Key': 'error.html'
        },
        'IndexDocument': {
            'Suffix': 'index.html'
        }
    })


def upload_file(s3_bucket, path, key):
    """Upload path to s3_bucket at key."""
    content_type = mimetypes.guess_type(key)[0] or 'text/plain'
    s3_bucket.upload_file(
        path,
        key,
        ExtraArgs={
            'ContentType': content_type
        })


@cli.command('sync')
@click.argument('pathname', type=click.Path(exists=True))
@click.argument('bucket')
def sync(pathname, bucket):
    """Sync contents of PATHNAME to BUCKET."""
    s3_bucket = S3.Bucket(bucket)
    root = Path(pathname).expanduser().resolve()

    def handle_directory(target):
        """Check if the target is a directory or file."""
        for path in target.iterdir():
            if path.is_dir():
                handle_directory(path)
            if path.is_file():
                upload_file(
                    s3_bucket,
                    str(path),
                    str(path.relative_to(root))
                    )

    handle_directory(root)


if __name__ == '__main__':
    cli()
