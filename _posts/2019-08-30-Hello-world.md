---
layout: post
current: post
cover: assets/images/sky.jpg
navigation: True
title: Hello world
date: 2019-08-30 19:55:23
tags: Develop, git
class: post-template
subclass: 'post tag-develop'
author: Woojune Park
---
# Hello, world!


I don't usually blog something, or anything actually. But I decided to document what I studied for future myself and the future employer (Yes, that means you).

As the my first Github page post (of many posts to come), I'll write about how to deploy Github page like this one and to install theme of your choice.


Before we begin, let's briefly go through why I choose Github page as my portfolio blog over many other blog services out there in the wild :

- Naver blog - Obviously no, as I won't be writing about sponsored eats & products. And I hate that LINE sticker.

- Kakao Tistory, Brunch - Even Kakao tech blog doesn't use those. There are good reasons for that.

- Wordpress - Too classic.

- Tumblr - This blog is for SFW contents only.


# Now let's begin!
Requirements:
- Github ID
 - Github desktop
- Ruby
 - Bundler
 - Jekyll


1. Install Ruby
DO NOT just google 'ruby' and install something comes up first.

https://jekyllrb.com/docs/installation/windows/
Go to the site above and follow instructions. Instructions are :
1) Download Ruby+Devkit version. (w/ recommended version number, which is stable one)
2) Use default options for installation.
3) Check the ridk install step on the last stage of the installation.
4) When CMD pops up, and asks to choose between 1, 2, 3, enter 3. (Actually, not so sure about this one, but it worked.)
5) Close the install CMD. (There's a bug in installer repeating 4) again.) 
6) Open a new CMD window from the start menu.


2. Install Jekyll & Bundler
1) Install(This takes 2~3 min.): 
		$ gem install jekyll bundler
2) Check if Jekyll installed properly: $ jekyll -v
3) If 'jekyll 4.0.0' or above comes up, then you're ready to go.


3. Install Theme
1) Fork a jekyll theme repo you want. (You can look for one at http://jekyllthemes.org/ or https://jekyllthemes.io/)
2) Change the name of the repo to (your-github-nickname).github.io
3) Clone forked repo to your desktop.
4) Open CMD and go to the theme file folder. (Psst, it's called cd.)
5) Create Gemfile: 
	$ bundle init
6) Add Jekyll : 
	$ bundle add jekyll
7) Install Ruby Gems: 
	$ bundle install
8) 
	$ bundle exec jekyll serve
9) Tinker _config.yml file.


4. Install Atom (you can skip this if you use other kramdown editers)
1) Install Atom: https://atom.io/
2) Install Kramdown: https://kramdown.gettalong.org/installation.html
		$ gem install kramdown
3) We need Node.js and stuff for this package to work. Install Node.js at https://nodejs.org/en/
4) Open windows power shell (NOT CMD) and type in:
		$ npm install --global --production windows-build-tools
5) Install Atom Kramdown Package: https://atom.io/packages/markdown-preview-kramdown

Alternatively, you can use a Chrome web app :
https://chrome.google.com/webstore/detail/jekyll-editor/dfdkgbhjmllemfblfoohhehdigokocme?hl=ko
