# tghook

A simple python `3.9+` library for creating telegram bots servers that exclusively use webhook for communication

> This project is in its infancy. It currently implements a minimum scope with a working HTTPS server and webhook setup,
> plus external calls to a user defined function for implementing the bot functionality.
>
> The API is **NOT** stable, and may change completely overnight.

## Documentation

Currently there are no plans to write one. The code is fairly small and reasonable commented.

If you want to know how to use this, check the examples below.

## Examples

Some real world use cases for this library:

- [url_to_video](./tghook/example/url_to_video.py):
  A simple bot that attempts to extract direct video URLs from websites using yt-dlp, check it live on telegram [here](https://t.me/get_videos_url_bot)

Copyright © 2021 Vítor Vasconcellos

> This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.
>
> This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
>
> You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
