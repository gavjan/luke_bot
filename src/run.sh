pip3 install BeautifulSoup4
pip3 install discord

send_mail() {
  echo "Sending error mail..."
  sed -i "s/\"/'/g" .err_file
  curl "https://api.postmarkapp.com/email" \
  -X POST \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "X-Postmark-Server-Token: $mail_token" \
  -d "{
  \"From\": \"$mail\",
  \"To\": \"$mail\",
  \"Subject\": \"[Luke] Bot Error\",
  \"TextBody\": \"$(cat .err_file)\",
  \"MessageStream\": \"outbound\"
  }"
}

while true; do
  python3 main.py 2>.err_file || send_mail
  git pull
done
