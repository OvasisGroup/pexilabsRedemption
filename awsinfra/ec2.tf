# Get the latest Amazon Linux 2 AMI
data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# EC2 Instance
resource "aws_instance" "main" {
  ami           = data.aws_ami.amazon_linux.id
  instance_type = "t3.small"
  
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.ec2_sg.id]
  associate_public_ip_address = true
  
  # Key pair for SSH access (optional - set variable if you have one)
  key_name = var.key_pair_name != "" ? var.key_pair_name : null

  # Root volume configuration (100GB as requested)
  root_block_device {
    volume_type = "gp3"
    volume_size = 100
    encrypted   = true
    
    tags = {
      Name = "pexilabs-root-volume"
    }
  }

  # User data script (optional - basic setup)
  user_data = <<-EOF
    #!/bin/bash
    yum update -y
    yum install -y htop
  EOF

  tags = {
    Name = var.instance_name
  }
}
